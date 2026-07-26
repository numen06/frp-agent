"""堡垒机式主机管理模型。"""
from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from app.database import Base


class ManagedHost(Base):
    """由系统代管 SSH 连接凭据的主机。"""

    __tablename__ = "managed_hosts"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False, index=True)
    address = Column(String(255), nullable=False)
    port = Column(Integer, nullable=False, default=22)
    host_type = Column(String(20), nullable=False, default="ssh")  # ssh | docker
    credential_id = Column(Integer, ForeignKey("ssh_credentials.id"), nullable=True)
    docker_credential_id = Column(
        Integer, ForeignKey("docker_credentials.id"), nullable=True
    )
    docker_use_tls = Column(Boolean, nullable=False, default=True)
    docker_verify_tls = Column(Boolean, nullable=False, default=True)
    docker_endpoint_id = Column(Integer, nullable=True)
    description = Column(Text, nullable=True)
    tags = Column(String(500), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    host_key_fingerprint = Column(String(100), nullable=True)
    last_status = Column(String(20), nullable=False, default="unknown")
    last_checked_at = Column(DateTime, nullable=True)
    last_message = Column(String(500), nullable=True)
    version_info = Column(String(500), nullable=True)
    created_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    credential = relationship("SshCredential")
    docker_credential = relationship("DockerCredential")
    grants = relationship(
        "HostAccessGrant", back_populates="host", cascade="all, delete-orphan"
    )
    audit_logs = relationship(
        "HostAuditLog", back_populates="host", cascade="all, delete-orphan"
    )


class HostAccessGrant(Base):
    """用户或 API Key 对单台主机的最小权限授权。"""

    __tablename__ = "host_access_grants"
    __table_args__ = (
        UniqueConstraint(
            "host_id", "subject_type", "subject_id", name="uq_host_access_subject"
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    host_id = Column(
        Integer, ForeignKey("managed_hosts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    subject_type = Column(String(20), nullable=False)  # user | api_key
    subject_id = Column(Integer, nullable=False, index=True)
    can_connect = Column(Boolean, nullable=False, default=True)
    can_execute = Column(Boolean, nullable=False, default=False)
    can_manage_docker = Column(Boolean, nullable=False, default=False)
    is_active = Column(Boolean, nullable=False, default=True)
    expires_at = Column(DateTime, nullable=True)
    created_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    host = relationship("ManagedHost", back_populates="grants")

    def is_expired(self) -> bool:
        return bool(self.expires_at and datetime.utcnow() > self.expires_at)


class HostAuditLog(Base):
    """主机访问审计日志。"""

    __tablename__ = "host_audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    host_id = Column(
        Integer, ForeignKey("managed_hosts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    actor_type = Column(String(20), nullable=False)
    actor_id = Column(Integer, nullable=False)
    actor_name = Column(String(200), nullable=False)
    action = Column(String(50), nullable=False)
    target = Column(String(255), nullable=True)
    command = Column(Text, nullable=True)
    status = Column(String(20), nullable=False)
    exit_code = Column(Integer, nullable=True)
    stdout = Column(Text, nullable=True)
    stderr = Column(Text, nullable=True)
    client_ip = Column(String(100), nullable=True)
    duration_ms = Column(Integer, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)

    host = relationship("ManagedHost", back_populates="audit_logs")
