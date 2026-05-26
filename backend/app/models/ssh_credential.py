"""SSH 凭据模型"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Text
from app.database import Base


class SshCredential(Base):
    """SSH 登录凭据（密钥字段加密存储）"""
    __tablename__ = "ssh_credentials"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    username = Column(String(100), nullable=False)
    auth_type = Column(String(20), nullable=False)  # password | private_key
    password_encrypted = Column(Text, nullable=True)
    private_key_encrypted = Column(Text, nullable=True)
    passphrase_encrypted = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
