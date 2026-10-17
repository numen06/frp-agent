"""Probe native RDP/TLS without credentials or a target login."""
import argparse
import json
import socket
import ssl
import struct


def read_exact(sock, size):
    data = b""
    while len(data) < size:
        chunk = sock.recv(size-len(data))
        if not chunk:
            raise RuntimeError("Unexpected end of RDP negotiation")
        data += chunk
    return data


def verify(host, port):
    with socket.create_connection((host, port), timeout=10) as sock:
        sock.sendall(bytes.fromhex("030000130ee000000000000100080001000000"))
        header = read_exact(sock, 4)
        length = struct.unpack("!H", header[2:])[0]
        if header[:2] != b"\x03\x00" or length < 12 or length > 4096:
            raise RuntimeError("Invalid RDP response")
        response = read_exact(sock, length-4)
        if response[-8] != 2 or struct.unpack("<I", response[-4:])[0] != 1:
            raise RuntimeError("Gateway did not negotiate mandatory TLS")
        context = ssl.create_default_context()
        context.minimum_version = ssl.TLSVersion.TLSv1_2
        with context.wrap_socket(sock, server_hostname=host) as tls:
            print(json.dumps({"gateway":f"{host}:{port}","rdp_tls":True,"tls_version":tls.version(),"certificate_verified":True,"windows_login_tested":False}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("host")
    parser.add_argument("port",type=int,nargs="?",default=13389)
    args=parser.parse_args()
    verify(args.host,args.port)
