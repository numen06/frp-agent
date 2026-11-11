"""Persistent metadata and encrypted secrets for native gateway credentials."""
from sqlalchemy import Column, DateTime, Index, Integer, LargeBinary, String

from app.database import Base


class TemporaryCredential(Base):
    __tablename__ = "temporary_credentials"
    __table_args__ = (
        Index("ix_temporary_credentials_owner_issued", "user_id", "issued_at"),
        Index("ix_temporary_credentials_protocol_expiry", "protocol", "expires_at"),
    )

    protocol = Column(String(3), primary_key=True)
    username = Column(String(32), primary_key=True)
    # Keep history for the retention period even when the account or host disappears.
    user_id = Column(Integer, nullable=False)
    host_id = Column(Integer, nullable=False)
    owner = Column(String(50), nullable=False)
    target = Column(String(100), nullable=False)
    address = Column(String(300), nullable=False)
    issued_at = Column(DateTime, nullable=False, index=True)
    expires_at = Column(DateTime, nullable=False, index=True)
    stamp = Column(String(64), nullable=True)
    encrypted_password = Column(LargeBinary, nullable=True)
    invalidated_at = Column(DateTime, nullable=True, index=True)
    invalidated_status = Column(String(7), nullable=True)
    uses = Column(Integer, nullable=False, default=0)
    last_used_at = Column(DateTime, nullable=True)
