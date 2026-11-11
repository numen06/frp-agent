"""Bounded, process-local catalog for native gateway temporary credentials."""
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import secrets
import time

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from fastapi import HTTPException


@dataclass
class Credential:
    username: str
    ticket: object
    owner: str
    target: str
    address: str
    issued_at: datetime
    expires_at: datetime
    encrypted_password: bytes
    revoked: bool = False
    consumed: bool = False
    uses: int = 0
    last_used_at: datetime | None = None

    @property
    def status(self):
        if self.revoked:
            return "revoked"
        if self.consumed:
            return "used"
        if self.ticket.expires <= time.monotonic():
            self.encrypted_password = b""
            return "expired"
        return "active"

    def use(self, *, consume=False):
        self.uses += 1
        self.last_used_at = datetime.now(timezone.utc)
        if consume:
            self.consumed = True
            self.encrypted_password = b""

    def revoke(self):
        self.revoked = True
        self.encrypted_password = b""


class TemporaryCredentials:
    def __init__(self, protocol, capacity, per_user, lock):
        self.protocol = protocol
        self.capacity = capacity
        self.per_user = per_user
        self.lock = lock
        self.rows = {}
        self.cipher = AESGCM(AESGCM.generate_key(bit_length=256))

    def issue(self, username, password, ticket, owner, target, address, duration):
        # Callers hold their gateway lock. Evict old history before adding a row,
        # while keeping every active credential available for authentication.
        active = [row for row in self.rows.values() if row.status == "active"]
        if len(active) >= self.capacity or sum(row.ticket.user_id == ticket.user_id for row in active) >= self.per_user:
            raise HTTPException(429, "有效的临时凭据过多，请撤销不再使用的凭据或等其到期")
        history_limit = self.capacity * 2
        for key, row in list(self.rows.items()):
            if len(self.rows) < history_limit:
                break
            if row.status != "active":
                del self.rows[key]
        now = datetime.now(timezone.utc)
        nonce = secrets.token_bytes(12)
        encrypted = nonce + self.cipher.encrypt(nonce, password.encode(), username.encode())
        row = Credential(username, ticket, owner, target, address, now,
                         now + timedelta(seconds=duration), encrypted)
        self.rows[username] = row
        return row

    def active(self, username):
        row = self.rows.get(username)
        return row if row is not None and row.status == "active" else None

    def reveal(self, row):
        if row.status != "active":
            raise HTTPException(410, "临时凭据已失效")
        encrypted = row.encrypted_password
        return self.cipher.decrypt(encrypted[:12], encrypted[12:], row.username.encode()).decode()

    def metadata(self, row, user_id):
        status = row.status
        return {
            "protocol": self.protocol, "username": row.username, "owner": row.owner,
            "host_id": row.ticket.host_id, "target": row.target, "address": row.address,
            "issued_at": row.issued_at, "expires_at": row.expires_at, "status": status,
            "uses": row.uses, "last_used_at": row.last_used_at,
            "can_copy": status == "active" and row.ticket.user_id == user_id,
        }

    def stop(self):
        for row in self.rows.values():
            if row.status == "active":
                row.revoke()
