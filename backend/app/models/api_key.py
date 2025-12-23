"""API Key 模型"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text
from app.database import Base


class ApiKey(Base):
    """API Key 表"""
    __tablename__ = "api_keys"
    
    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(64), unique=True, index=True, nullable=False)  # API Key 值（哈希后的）
    key_encrypted = Column(Text, nullable=True)  # 加密后的原始密钥（可选，用于前端显示）
    description = Column(String(200), nullable=False)  # 描述（必须）
    expires_at = Column(DateTime, nullable=True)  # 过期时间（可选）
    is_active = Column(Boolean, default=True, nullable=False)  # 是否激活
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_used_at = Column(DateTime, nullable=True)  # 最后使用时间
    
    def __repr__(self):
        return f"<ApiKey(id={self.id}, description='{self.description}', is_active={self.is_active})>"
    
    def is_expired(self) -> bool:
        """检查是否已过期"""
        if self.expires_at is None:
            return False
        return datetime.utcnow() > self.expires_at

