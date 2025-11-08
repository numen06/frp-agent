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
    group_name = Column(String(50), nullable=True, index=True)  # 分组名称，从代理名称中解析
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
    
    @staticmethod
    def parse_group_name(proxy_name: str) -> str:
        """从代理名称中解析分组名称
        
        例如: dlyy_rdp -> dlyy
        
        Args:
            proxy_name: 代理名称
            
        Returns:
            分组名称，如果没有下划线则返回"其他"
        """
        if "_" in proxy_name:
            group = proxy_name.split("_")[0]
            return group if group else "其他"
        return "其他"
    
    def __repr__(self):
        return f"<Proxy(id={self.id}, name='{self.name}', group='{self.group_name}', type='{self.proxy_type}', status='{self.status}')>"

