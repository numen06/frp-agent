"""Database-backed credentials shared by the native gateways."""
import json
import os
import secrets
from datetime import datetime, timedelta, timezone
from pathlib import Path
from tempfile import NamedTemporaryFile

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from fastapi import HTTPException
from sqlalchemy import and_, or_

from app.config import get_settings
from app.database import SessionLocal
from app.models.temporary_credential import TemporaryCredential

RETENTION = timedelta(days=7)


def utcnow():
    # The application stores SQL timestamps as naive UTC.
    return datetime.now(timezone.utc).replace(tzinfo=None)


def utc_iso(value):
    return value.replace(tzinfo=timezone.utc).isoformat() if value is not None else None


def key_path(db):
    configured = get_settings().temporary_credential_key_path
    if configured:
        return Path(configured)
    url = db.get_bind().url
    if url.get_backend_name() == "sqlite" and url.database not in (None, "", ":memory:"):
        return Path(url.database).with_name(Path(url.database).name + ".temporary-credentials.key")
    return Path("data/temporary_credentials.key")


def cipher(db, *, create=False):
    path = key_path(db)
    if create and not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        # Publish a complete owner-only key atomically, including on concurrent startup.
        with NamedTemporaryFile(dir=path.parent) as candidate:
            candidate.write(AESGCM.generate_key(bit_length=256))
            candidate.flush()
            try:
                os.link(candidate.name, path)
            except FileExistsError:
                pass
    return AESGCM(path.read_bytes())


def binding(row):
    return json.dumps([row.protocol, row.username, row.user_id, row.host_id, row.stamp,
                       utc_iso(row.expires_at)], separators=(",", ":")).encode()


def retained(db, now):
    cutoff = now - RETENTION
    row = TemporaryCredential
    return db.query(row).filter(or_(
        row.invalidated_at > cutoff,
        and_(row.invalidated_at.is_(None), row.expires_at > cutoff),
    ))


def cleanup_temporary_credentials(db=None):
    if db is None:
        with SessionLocal() as session:
            cleanup_temporary_credentials(session)
        return
    now = utcnow()
    row = TemporaryCredential
    db.query(row).filter(
        or_(row.invalidated_at <= now - RETENTION,
            and_(row.invalidated_at.is_(None), row.expires_at <= now - RETENTION)),
    ).delete(synchronize_session=False)
    db.query(row).filter(row.invalidated_at.is_(None), row.expires_at <= now).update({
        row.invalidated_at: row.expires_at,
        row.invalidated_status: "expired",
        row.encrypted_password: None,
        row.stamp: None,
    }, synchronize_session=False)
    db.commit()


class TemporaryCredentials:
    def __init__(self, protocol, capacity, per_user, lock):
        self.protocol = protocol
        self.capacity = capacity
        self.per_user = per_user
        self.lock = lock

    def _active(self, query, now):
        row = TemporaryCredential
        return query.filter(row.protocol == self.protocol, row.invalidated_at.is_(None),
                            row.expires_at > now)

    def issue(self, db, username, password, user, host, address, stamp, duration):
        now = utcnow()
        active = self._active(db.query(TemporaryCredential), now)
        if active.count() >= self.capacity or active.filter_by(user_id=user.id).count() >= self.per_user:
            raise HTTPException(429, "有效的临时凭据过多，请撤销不再使用的凭据或等其到期")
        row = TemporaryCredential(
            protocol=self.protocol, username=username, user_id=user.id, host_id=host.id,
            owner=user.username, target=host.name, address=address, stamp=stamp,
            issued_at=now, expires_at=now + timedelta(seconds=duration),
        )
        nonce = secrets.token_bytes(12)
        row.encrypted_password = nonce + cipher(db, create=True).encrypt(nonce, password.encode(), binding(row))
        db.add(row)
        return row

    def get(self, db, username):
        return retained(db, utcnow()).filter_by(protocol=self.protocol, username=username).populate_existing().one_or_none()

    def active(self, db, username):
        return self._active(db.query(TemporaryCredential), utcnow()).filter_by(
            username=username,
        ).populate_existing().one_or_none()

    def reveal(self, db, row):
        if self.status(row) != "active":
            raise HTTPException(410, "临时凭据已失效")
        encrypted = row.encrypted_password
        try:
            return cipher(db).decrypt(encrypted[:12], encrypted[12:], binding(row)).decode()
        except (FileNotFoundError, InvalidTag, ValueError, TypeError):
            self.revoke(db, row)
            db.commit()
            raise HTTPException(410, "临时凭据已失效") from None

    def use(self, db, row, *, consume=False):
        now = utcnow()
        model = TemporaryCredential
        values = {model.uses: model.uses + 1, model.last_used_at: now}
        if consume:
            values.update({model.invalidated_at: now, model.invalidated_status: "used",
                           model.encrypted_password: None, model.stamp: None})
        return self._active(db.query(model), now).filter_by(username=row.username).update(
            values, synchronize_session=False,
        ) == 1

    def revoke(self, db, row):
        now = utcnow()
        model = TemporaryCredential
        return self._active(db.query(model), now).filter_by(username=row.username).update({
            model.invalidated_at: now, model.invalidated_status: "revoked",
            model.encrypted_password: None, model.stamp: None,
        }, synchronize_session=False) == 1

    @staticmethod
    def status(row):
        return row.invalidated_status or ("expired" if row.expires_at <= utcnow() else "active")

    def metadata(self, row, user_id):
        status = self.status(row)
        return {
            "protocol": self.protocol, "username": row.username, "owner": row.owner,
            "host_id": row.host_id, "target": row.target, "address": row.address,
            "issued_at": utc_iso(row.issued_at), "expires_at": utc_iso(row.expires_at),
            "status": status, "uses": row.uses, "last_used_at": utc_iso(row.last_used_at),
            "invalidated_at": utc_iso(row.invalidated_at or (row.expires_at if status == "expired" else None)),
            "can_copy": status == "active" and row.user_id == user_id,
        }
