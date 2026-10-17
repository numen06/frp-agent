"""Docker Engine API 凭据模型。"""
from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String, Text

from app.database import Base


class DockerCredential(Base):
    """Portainer API Key 或用户名/密码凭据。"""

    __tablename__ = "docker_credentials"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    auth_type = Column(String(20), nullable=False)  # api_key | password
    username = Column(String(100), nullable=True)
    password_encrypted = Column(Text, nullable=True)
    api_key_encrypted = Column(Text, nullable=True)
    ca_cert_encrypted = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )
