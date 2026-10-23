"""内置 frps 的单例配置，随 data 数据库持久化。"""
from sqlalchemy import Boolean, Column, Integer, String, Text

from app.database import Base


class BuiltinFrpsConfig(Base):
    __tablename__ = "builtin_frps_config"

    id = Column(Integer, primary_key=True, default=1)
    enabled = Column(Boolean, nullable=False, default=False)
    onboarding_seen = Column(Boolean, nullable=False, default=False)
    public_addr = Column(String(255), nullable=False, default="")
    bind_port = Column(Integer, nullable=False, default=7000)
    dashboard_port = Column(Integer, nullable=False, default=7500)
    proxy_port_start = Column(Integer, nullable=False, default=6000)
    proxy_port_end = Column(Integer, nullable=False, default=6099)
    vhost_http_port = Column(Integer, nullable=False, default=0)
    vhost_https_port = Column(Integer, nullable=False, default=0)
    tls_force = Column(Boolean, nullable=False, default=True)
    token_encrypted = Column(String(1000), nullable=False, default="")
    dashboard_password_encrypted = Column(String(1000), nullable=False, default="")
    raw_config_encrypted = Column(Text, nullable=True)
