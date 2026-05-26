"""GitHub 安装包同步任务模型"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Text
from app.database import Base


class PackageSyncJob(Base):
    """从 GitHub 后台下载安装包的同步任务"""
    __tablename__ = "package_sync_jobs"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(String(36), unique=True, nullable=False, index=True)
    status = Column(String(20), nullable=False, default="queued")  # queued/running/completed/failed
    version = Column(String(50), nullable=False)
    platforms = Column(Text, nullable=True)  # JSON array
    download_source = Column(String(20), nullable=False, default="origin")
    total = Column(Integer, nullable=False, default=0)
    completed = Column(Integer, nullable=False, default=0)
    results = Column(Text, nullable=True)  # JSON list of per-platform results
    error = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)
