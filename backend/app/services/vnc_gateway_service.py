"""Authenticated public listener for the built-in macOS Screen Sharing client."""
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
from app.services.temporary_credentials import TemporaryCredentials

logger = logging.getLogger(__name__)
TICKET_AGE = 180


@dataclass(frozen=True)
class Ticket:
    user_id: int
    host_id: int
    salt: bytes
    verifier: int
    expires: float
    password_stamp: str
    target_state: tuple


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
        with self.lock:
            self.temporary_credentials.stop()

    def issue(self, db, user, host_id, address, client_ip):
        if not self.running:
            raise HTTPException(503, "原生 VNC 网关尚未启用")
        host = active_vnc_host(db, user, host_id)
        name = secrets.token_hex(12)
        password = secrets.token_hex(16)
        salt = secrets.token_bytes(32)
        now = time.monotonic()
        with self.lock:
            ticket = Ticket(
                user.id, host_id, salt, verifier_for(password.encode(), salt), now + TICKET_AGE,
                user.password_hash, snapshot(db, host),
            )
            row = self.temporary_credentials.issue(name, password, ticket, user.username, host.name, address, TICKET_AGE)
            try:
                add_audit_log(db, host, user, "vnc_ticket_issued", "success", client_ip, target=host.name)
            except Exception:
                row.revoke()
                raise
        return {"username": name, "password": password, "address": address, "expires_in": TICKET_AGE,
                "expires_at": row.expires_at.isoformat()}

    def lookup(self, name):
        with self.lock:
            row = self.temporary_credentials.active(name.decode("ascii", errors="replace"))
            return row.ticket if row else None

    def consume(self, name, ticket):
        with self.lock:
            row = self.temporary_credentials.active(name.decode("ascii", errors="replace"))
            if not row or row.ticket is not ticket:
                return False
            row.use(consume=True)
            return True

    def validate_temporary_credential(self, db, ticket):
        user = db.get(User, ticket.user_id)
        if user is None or user.password_hash != ticket.password_stamp:
            raise HTTPException(403, "账号或密码已变更")
        return user, active_vnc_host(db, user, ticket.host_id, ticket.target_state)

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
                state = ticket.target_state
                client, upstream, initial = open_vnc(db, host)
            with SessionLocal() as db:
                active_vnc_host(db, user, ticket.host_id, state)
            records = EncryptedRecords(channel, initial, wrap_key)
            upstream.settimeout(5)
            self.relay(records, upstream, ticket, user, state, traffic)
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

    def relay(self, records, upstream, ticket, user, state, traffic):
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
                    active_vnc_host(db, user, ticket.host_id, state)
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
