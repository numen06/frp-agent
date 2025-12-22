"""分组模型"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from app.database import Base


class Group(Base):
    """分组表"""
    __tablename__ = "groups"
    
    id = Column(Integer, primary_key=True, index=True)
    frps_server_id = Column(Integer, ForeignKey("frps_servers.id"), nullable=False, index=True)
    name = Column(String(50), nullable=False, index=True)
    description = Column(String(200), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # 唯一约束：同一服务器下分组名称不能重复
    __table_args__ = (
        UniqueConstraint('frps_server_id', 'name', name='uq_server_group_name'),
    )
    
    # 关系
    frps_server = relationship("FrpsServer", back_populates="groups")
    
    def __repr__(self):
        return f"<Group(id={self.id}, name='{self.name}', server_id={self.frps_server_id})>"

