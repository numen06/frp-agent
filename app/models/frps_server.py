"""frps 服务器配置模型"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.orm import relationship
from app.database import Base


class FrpsServer(Base):
    """frps 服务器配置表"""
    __tablename__ = "frps_servers"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, unique=True)
    server_addr = Column(String(255), nullable=False)
    server_port = Column(Integer, nullable=False, default=7000)
    api_base_url = Column(String(255), nullable=False)
    auth_username = Column(String(100), nullable=False)
    auth_password = Column(String(255), nullable=False)
    auth_token = Column(String(255), nullable=True)  # FRP 认证 token
    is_active = Column(Boolean, default=True, nullable=False)
    last_test_status = Column(String(20), default="unknown", nullable=False)  # online, offline, unknown
    last_test_time = Column(DateTime, nullable=True)
    last_test_message = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # 关系
    proxies = relationship("Proxy", back_populates="frps_server", cascade="all, delete-orphan")
    port_allocations = relationship("PortAllocation", back_populates="frps_server", cascade="all, delete-orphan")
    proxy_histories = relationship("ProxyHistory", back_populates="frps_server", cascade="all, delete-orphan")
    groups = relationship("Group", back_populates="frps_server", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<FrpsServer(id={self.id}, name='{self.name}', addr='{self.server_addr}:{self.server_port}')>"

