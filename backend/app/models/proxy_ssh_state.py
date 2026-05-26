"""代理 SSH 扫描状态模型"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.database import Base


class ProxySshState(Base):
    """单代理 SSH 升级扫描状态"""
    __tablename__ = "proxy_ssh_states"

    id = Column(Integer, primary_key=True, index=True)
    proxy_id = Column(Integer, ForeignKey("proxies.id"), nullable=False, unique=True, index=True)
    credential_id = Column(Integer, ForeignKey("ssh_credentials.id"), nullable=True)
    install_path = Column(String(500), nullable=True)
    is_ssh_candidate = Column(Boolean, nullable=False, default=False)
    reachable = Column(Boolean, nullable=True)
    platform = Column(String(50), nullable=True)
    current_version = Column(String(100), nullable=True)
    target_version = Column(String(50), nullable=True)
    target_package_id = Column(Integer, ForeignKey("frp_packages.id"), nullable=True)
    upgradeable = Column(Boolean, nullable=False, default=False)
    status = Column(String(50), nullable=False, default="unknown")
    message = Column(Text, nullable=True)
    last_scanned_at = Column(DateTime, nullable=True)
    last_upgraded_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    proxy = relationship("Proxy", backref="ssh_state", uselist=False)
    credential = relationship("SshCredential")
    target_package = relationship("FrpPackage")
