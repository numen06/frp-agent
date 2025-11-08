"""端口分配模型"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base


class PortAllocation(Base):
    """端口分配记录表"""
    __tablename__ = "port_allocations"
    
    id = Column(Integer, primary_key=True, index=True)
    frps_server_id = Column(Integer, ForeignKey("frps_servers.id"), nullable=False, index=True)
    port = Column(Integer, nullable=False, index=True)
    is_allocated = Column(Boolean, default=True, nullable=False)
    allocated_to = Column(String(100), nullable=True)  # 分配给哪个代理
    allocated_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # 关系
    frps_server = relationship("FrpsServer", back_populates="port_allocations")
    
    def __repr__(self):
        return f"<PortAllocation(id={self.id}, port={self.port}, allocated_to='{self.allocated_to}')>"

