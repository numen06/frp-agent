"""Apple Screen Sharing's RSA-SRP handshake and encrypted RFB records.

Wire format based on the Apple interoperability notes in iShareScreen and
verified against Screen Sharing.app. The SRP group is from RFC 5054 A.5.
"""
import hashlib
import hmac
import secrets
import struct
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

from app.services.vnc_service import read_exact

VERSION = b"RFB 003.889\n"
GROUP = bytes.fromhex(Path(__file__).with_name("rfc5054-4096.txt").read_text())
MODULUS = int.from_bytes(GROUP, "big")
GENERATOR = 5
ITERATIONS = 35000
OPTIONS = b"mda=SHA-512,replay_detection,conf+int=ChaCha20-Poly1305,kdf=SALTED-SHA512-PBKDF2"


def digest(data):
    return hashlib.sha512(data).digest()


def number(value, length):
    return value.to_bytes(length, "big")


def field(data, width):
    return number(len(data), width) + data


def require(condition):
    if not condition:
        raise ValueError("Invalid Apple Screen Sharing handshake")


def verifier_for(password, salt):
    stretched = hashlib.pbkdf2_hmac("sha512", password, salt, ITERATIONS, 128)
    exponent = int.from_bytes(digest(salt + digest(b":" + stretched)), "big")
    return pow(GENERATOR, exponent, MODULUS)


MULTIPLIER = int.from_bytes(digest(GROUP + number(GENERATOR, 512)), "big")
GROUP_HASH = bytes(a ^ b for a, b in zip(digest(GROUP), digest(number(GENERATOR, 512))))


def rsa_packet(channel):
    size = int.from_bytes(read_exact(channel, 4), "big")
    require(10 <= size <= 2048)
    data = read_exact(channel, size)
    require(data[:6] == b"\x01\x00RSA1")
    operation, length = struct.unpack_from("!HH", data, 6)
    require(length <= size - 10)
    return operation, data[10:10 + length]


def srp_packet(payload):
    return field(struct.pack("!IHI", 2, len(payload) + 4, len(payload)) + payload, 4)


def authenticate(channel, key, lookup, consume):
    channel.sendall(VERSION)
    require(read_exact(channel, 12) == VERSION)
    # Screen Sharing discovers the account dialog from the pair of SRP types.
    # Only RSA-SRP is accepted; legacy DES and DH never run on this listener.
    channel.sendall(b"\x02\x21\x24")
    require(read_exact(channel, 1) == b"\x21")
    operation, payload = rsa_packet(channel)
    if operation == 0 and not payload:
        public = key.public_key().public_bytes(
            serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo
        )
        channel.sendall(field(b"\x00\x01" + field(public, 4) + b"\0", 4))
        operation, payload = rsa_packet(channel)
    require(operation == 2 and len(payload) == 256)
    identity = key.decrypt(payload, padding.PKCS1v15())
    require(len(identity) >= 11)
    total, name_size = struct.unpack_from("!II", identity)
    require(total == len(identity) - 4 and 1 <= name_size <= 64 and len(identity) == 11 + name_size)
    ticket_name = identity[8:8 + name_size]
    ticket = lookup(ticket_name)
    salt = ticket.salt if ticket else secrets.token_bytes(32)
    verifier = ticket.verifier if ticket else verifier_for(secrets.token_bytes(32), salt)
    secret = secrets.randbits(512) or 1
    public = number((MULTIPLIER * verifier + pow(GENERATOR, secret, MODULUS)) % MODULUS, 512)
    challenge = (b"\0" + field(GROUP, 2) + field(b"\x05", 2) + field(salt, 1)
                 + field(public, 2) + number(ITERATIONS, 8) + field(OPTIONS, 2))
    channel.sendall(srp_packet(challenge))
    operation, proof = rsa_packet(channel)
    require(operation == 2 and len(proof) >= 583)
    reserved, inner_size, public_size = struct.unpack_from("!HHH", proof)
    require(reserved == 0 and inner_size == len(proof) - 4 and public_size == 512)
    peer = proof[6:518]
    require(proof[518] == 64)
    proof_digest = proof[519:583]
    peer_number = int.from_bytes(peer, "big")
    require(0 < peer_number < MODULUS)
    mix = int.from_bytes(digest(peer + public), "big")
    require(mix != 0)
    shared = pow(peer_number * pow(verifier, mix, MODULUS) % MODULUS, secret, MODULUS)
    session_key = digest(number(shared, 512))
    expected = digest(GROUP_HASH + digest(b"") + salt + peer + public + session_key)
    require(hmac.compare_digest(proof_digest, expected) and ticket is not None and consume(ticket_name, ticket))
    server_proof = digest(peer + proof_digest + session_key)
    channel.sendall(srp_packet(field(server_proof, 1) + field(secrets.token_bytes(16), 1) + bytes(6)) + bytes(4))
    require(read_exact(channel, 1) == b"\xc1")
    return ticket, hashlib.sha256(session_key).digest()[:16]


class EncryptedRecords:
    def __init__(self, channel, initial, wrap_key):
        self.channel = channel
        self.wrap_key = wrap_key
        self.key, iv = secrets.token_bytes(16), secrets.token_bytes(16)
        wrapper = Cipher(algorithms.AES(wrap_key), modes.ECB()).encryptor()
        rekey = struct.pack("!BBHHHHHiI", 0, 0, 1, 0, 0, 0, 0, 1103, 1)
        channel.sendall(initial[:20] + field(bytes(22) + initial[24:], 4)
                        + rekey + wrapper.update(self.key + iv) + wrapper.finalize())
        cipher = Cipher(algorithms.AES(self.key), modes.CBC(iv))
        self.reader, self.writer = cipher.decryptor(), cipher.encryptor()
        self.received = self.sent = 0

    def read(self):
        prefix = read_exact(self.channel, 2, timeout=5)
        if not self.received:
            if prefix == b"\x21\0":
                size = int.from_bytes(read_exact(self.channel, 2), "big")
                require(size <= 4096)
                read_exact(self.channel, size)
                return b""
            if prefix == b"\x0a\0":
                read_exact(self.channel, 2)
                return b""
            if prefix == b"\x12\0":
                command = int.from_bytes(read_exact(self.channel, 2), "big")
                require(command in (1, 2))
                read_exact(self.channel, 8 if command == 1 else 4)
                return b""
        size = int.from_bytes(prefix, "big")
        require(32 <= size <= 65520 and size % 16 == 0)
        clear = self.reader.update(read_exact(self.channel, size, timeout=5))
        tag = hashlib.sha1(number(self.received, 4) + clear[:-20]).digest()
        require(hmac.compare_digest(clear[-20:], tag))
        length = int.from_bytes(clear[:2], "big")
        require(0 < length <= size - 22 and size - 22 - length < 16)
        self.received += 1
        return clear[2:2 + length]

    def send(self, data):
        for offset in range(0, len(data), 60000):
            body = field(data[offset:offset + 60000], 2)
            body += secrets.token_bytes((-(len(body) + 20)) % 16)
            body += hashlib.sha1(number(self.sent, 4) + body).digest()
            self.channel.sendall(field(self.writer.update(body), 2))
            self.sent += 1

    def key_event(self, body):
        for key in (self.key, self.wrap_key):
            decoder = Cipher(algorithms.AES(key), modes.ECB()).decryptor()
            event = decoder.update(body[2:]) + decoder.finalize()
            if event[0] == 255 and event[1] in (0, 1):
                return b"\x04" + event[1:2] + bytes(2) + event[2:6]
        return b""
