"""FRP 安装包模型"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Boolean
from app.database import Base


class FrpPackage(Base):
    """frp 安装包表"""
    __tablename__ = "frp_packages"

    id = Column(Integer, primary_key=True, index=True)
    version = Column(String(50), nullable=False, index=True)
    platform = Column(String(50), nullable=False, index=True)
    filename = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_size = Column(Integer, nullable=False, default=0)
    source = Column(String(20), nullable=False, default="upload")  # github / upload
    download_url = Column(String(500), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    downloaded_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    sha256_checksum = Column(String(64), nullable=True)

    def __repr__(self):
        return f"<FrpPackage(id={self.id}, version='{self.version}', platform='{self.platform}')>"
