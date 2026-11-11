"""Authenticated public listener for the built-in macOS Screen Sharing client."""
import hashlib
import hmac
import json
import logging
import os
import secrets
import select
import socketserver
import threading
import time
from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import HTTPException

from app.config import get_settings
from app.database import SessionLocal
from app.models import ManagedHost, User
from app.services.host_access_service import add_audit_log
from app.services.vnc_apple_protocol import EncryptedRecords, authenticate, verifier_for
from app.services.vnc_service import active_vnc_host, open_vnc, snapshot
from app.services.temporary_credentials import TemporaryCredentials, utc_iso

logger = logging.getLogger(__name__)
TICKET_AGE = 180


@dataclass(frozen=True)
class Ticket:
    user_id: int
    host_id: int
    stamp: str
    salt: bytes
    verifier: int


class Listener(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True

    def __init__(self, address, gateway):
        self.gateway = gateway
        self.slots = threading.BoundedSemaphore(24)
        self.lock = threading.Lock()
        self.sources = {}
        super().__init__(address, Client)

    def verify_request(self, request, address):
        with self.lock:
            count = self.sources.get(address[0], 0)
            if count >= 4 or not self.slots.acquire(blocking=False):
                return False
            self.sources[address[0]] = count + 1
            return True

    def process_request(self, request, address):
        try:
            super().process_request(request, address)
        except BaseException:
            self.release(address)
            raise

    def process_request_thread(self, request, address):
        try:
            super().process_request_thread(request, address)
        finally:
            self.release(address)

    def release(self, address):
        with self.lock:
            count = self.sources[address[0]]
            if count == 1:
                del self.sources[address[0]]
            else:
                self.sources[address[0]] = count - 1
            self.slots.release()


class Client(socketserver.BaseRequestHandler):
    def handle(self):
        self.server.gateway.handle(self.request, self.client_address[0])


class VncGatewayService:
    def __init__(self):
        self.listener = None
        self.thread = None
        self.key = None
        self.lock = threading.Lock()
        self.temporary_credentials = TemporaryCredentials("vnc", 128, 4, self.lock)

    @property
    def running(self):
        return self.listener is not None

    def start(self):
        settings = get_settings()
        if self.running or not settings.vnc_gateway_enabled:
            return
        path = Path(settings.vnc_gateway_key_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
            with os.fdopen(os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600), "wb") as stream:
                stream.write(key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                                               serialization.NoEncryption()))
        key = serialization.load_pem_private_key(path.read_bytes(), password=None)
        if not isinstance(key, rsa.RSAPrivateKey) or key.key_size != 2048:
            raise ValueError("The Apple Screen Sharing gateway requires a 2048-bit RSA key")
        self.key = key
        self.listener = Listener((settings.vnc_gateway_host, settings.vnc_gateway_port), self)
        self.thread = threading.Thread(target=self.listener.serve_forever, daemon=True, name="vnc-gateway")
        self.thread.start()

    def stop(self):
        listener, self.listener = self.listener, None
        if listener:
            listener.shutdown()
            listener.server_close()
            self.thread.join(timeout=2)

    def issue(self, db, user, host_id, address, client_ip):
        if not self.running:
            raise HTTPException(503, "原生 VNC 网关尚未启用")
        host = active_vnc_host(db, user, host_id)
        name = secrets.token_hex(12)
        password = secrets.token_hex(16)
        with self.lock:
            row = self.temporary_credentials.issue(
                db, name, password, user, host, address, self._stamp(db, user, host), TICKET_AGE,
            )
            expires_at = utc_iso(row.expires_at)
            add_audit_log(db, host, user, "vnc_ticket_issued", "success", client_ip, target=host.name)
        return {"username": name, "password": password, "address": address, "expires_in": TICKET_AGE,
                "expires_at": expires_at}

    def lookup(self, name):
        with self.lock, SessionLocal() as db:
            row = self.temporary_credentials.active(db, name.decode("ascii", errors="replace"))
            if row is None:
                return None
            try:
                self.validate_temporary_credential(db, row)
            except HTTPException:
                self.temporary_credentials.revoke(db, row)
                db.commit()
                return None
            try:
                password = self.temporary_credentials.reveal(db, row)
            except HTTPException:
                return None
            salt = secrets.token_bytes(32)
            return Ticket(row.user_id, row.host_id, row.stamp, salt, verifier_for(password.encode(), salt))

    def consume(self, name, ticket):
        with self.lock, SessionLocal() as db:
            row = self.temporary_credentials.active(db, name.decode("ascii", errors="replace"))
            if row is None or (row.user_id, row.host_id, row.stamp) != (ticket.user_id, ticket.host_id, ticket.stamp):
                return False
            used = self.temporary_credentials.use(db, row, consume=True)
            db.commit()
            return used

    @staticmethod
    def _stamp(db, user, host):
        return hashlib.sha256(json.dumps([user.password_hash, snapshot(db, host)]).encode()).hexdigest()

    def validate_temporary_credential(self, db, ticket):
        user = db.get(User, ticket.user_id)
        if user is None:
            raise HTTPException(403, "账号或密码已变更")
        host = active_vnc_host(db, user, ticket.host_id)
        if not hmac.compare_digest(ticket.stamp or "", self._stamp(db, user, host)):
            raise HTTPException(403, "账号、主机或凭据已变更")
        return user, host

    def handle(self, channel, ip):
        ticket = user = client = upstream = None
        traffic = [0, 0]
        error = None
        started = time.monotonic()
        try:
            channel.settimeout(5)
            ticket, wrap_key = authenticate(channel, self.key, self.lookup, self.consume)
            with SessionLocal() as db:
                user, host = self.validate_temporary_credential(db, ticket)
                client, upstream, initial = open_vnc(db, host)
            with SessionLocal() as db:
                self.validate_temporary_credential(db, ticket)
            records = EncryptedRecords(channel, initial, wrap_key)
            upstream.settimeout(5)
            self.relay(records, upstream, ticket, traffic)
        except HTTPException as exc:
            error = exc.detail
        except (EOFError, OSError, ValueError):
            if not traffic[1]:
                error = "原生 VNC 协商或连接中断"
        except Exception:
            error = "原生 VNC 会话失败"
            logger.exception("Native VNC session failed")
        finally:
            for resource in (upstream, client):
                if resource:
                    with suppress(Exception):
                        resource.close()
            if ticket and user is not None:
                with SessionLocal() as db:
                    host = db.get(ManagedHost, ticket.host_id)
                    if host:
                        add_audit_log(db, host, user, "vnc_session", "failed" if error else "success", ip,
                                      target=f"VNC #{host.id}（原生网关）", error=error,
                                      bytes_sent=traffic[0], bytes_received=traffic[1],
                                      duration_ms=int((time.monotonic() - started) * 1000))

    def relay(self, records, upstream, ticket, traffic):
        started = touched = time.monotonic()
        next_check = started + 5
        next_update = started
        update = None
        waiting = False
        automatic = False
        while self.running:
            now = time.monotonic()
            if now - started >= 3600 or now - touched >= 900:
                return
            if now >= next_check:
                with SessionLocal() as db:
                    self.validate_temporary_credential(db, ticket)
                next_check = now + 5
            if automatic and update and not waiting and now >= next_update:
                upstream.sendall(update)
                waiting = True
            ready, _, _ = select.select([records.channel, upstream], [], [], 0.25)
            if records.channel in ready:
                body = records.read()
                if body[:1] == b"\x09" and len(body) == 16:
                    automatic = True
                data = upstream_message(records, body)
                if data:
                    upstream.sendall(data)
                    traffic[0] += len(data)
                    touched = now
                    if data[0] == 3:
                        update = b"\x03\x01" + data[2:]
                        waiting = True
            if upstream in ready:
                data = upstream.recv(32768)
                if not data:
                    return
                records.send(data)
                traffic[1] += len(data)
                waiting = False
                next_update = now + 0.25


def upstream_message(records, body):
    if not body:
        return b""
    kind = body[0]
    size = len(body)
    if kind == 16 and size == 18:
        return records.key_event(body)
    if (kind, size) in ((0, 20), (3, 10), (4, 8), (5, 6)):
        return body
    if kind == 2 and size >= 4 and size == 4 + 4 * int.from_bytes(body[2:4], "big"):
        # Request only RFB encodings shared with standard upstream servers.
        supported = {0, 1, 2, 5, 6, 7, 16, -223, -239}
        encodings = [body[i:i+4] for i in range(4, size, 4)
                     if int.from_bytes(body[i:i+4], "big", signed=True) in supported]
        return b"\x02\0" + len(encodings).to_bytes(2, "big") + b"".join(encodings)
    return b""


vnc_gateway_service = VncGatewayService()
