"""客户端升级任务模型"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from app.database import Base


class ClientUpgradeJob(Base):
    """SSH 扫描/升级批量任务"""
    __tablename__ = "client_upgrade_jobs"

    id = Column(Integer, primary_key=True, index=True)
    job_type = Column(String(20), nullable=False)  # scan | upgrade
    scope_type = Column(String(20), nullable=False)  # proxy | group
    frps_server_id = Column(Integer, ForeignKey("frps_servers.id"), nullable=True)
    group_name = Column(String(50), nullable=True)
    proxy_id = Column(Integer, ForeignKey("proxies.id"), nullable=True)
    credential_id = Column(Integer, ForeignKey("ssh_credentials.id"), nullable=True)
    status = Column(String(30), nullable=False, default="queued")
    total_count = Column(Integer, nullable=False, default=0)
    success_count = Column(Integer, nullable=False, default=0)
    failed_count = Column(Integer, nullable=False, default=0)
    skipped_count = Column(Integer, nullable=False, default=0)
    summary = Column(Text, nullable=True)
    result_json = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)
