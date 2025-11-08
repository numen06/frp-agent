"""代理历史记录模型"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base


class ProxyHistory(Base):
    """代理历史记录表"""
    __tablename__ = "proxy_history"
    
    id = Column(Integer, primary_key=True, index=True)
    frps_server_id = Column(Integer, ForeignKey("frps_servers.id"), nullable=False, index=True)
    proxy_name = Column(String(100), nullable=False, index=True)
    action = Column(String(50), nullable=False)  # online, offline, conflict, port_allocated, port_released
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    details = Column(Text, nullable=True)  # JSON 格式的详细信息
    
    # 关系
    frps_server = relationship("FrpsServer", back_populates="proxy_histories")
    
    def __repr__(self):
        return f"<ProxyHistory(id={self.id}, proxy='{self.proxy_name}', action='{self.action}')>"

