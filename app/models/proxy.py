"""代理记录模型"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base


class Proxy(Base):
    """代理记录表"""
    __tablename__ = "proxies"
    
    id = Column(Integer, primary_key=True, index=True)
    frps_server_id = Column(Integer, ForeignKey("frps_servers.id"), nullable=False, index=True)
    name = Column(String(100), nullable=False, index=True)
    proxy_type = Column(String(20), nullable=False, default="tcp")  # tcp, udp, http, https, stcp, xtcp
    remote_port = Column(Integer, nullable=True)  # TCP/UDP 代理的远程端口
    local_ip = Column(String(50), nullable=False, default="127.0.0.1")
    local_port = Column(Integer, nullable=False)
    client_name = Column(String(100), nullable=True)  # 客户端名称
    status = Column(String(20), default="offline")  # online, offline
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # 关系
    frps_server = relationship("FrpsServer", back_populates="proxies")
    
    def __repr__(self):
        return f"<Proxy(id={self.id}, name='{self.name}', type='{self.proxy_type}', status='{self.status}')>"

