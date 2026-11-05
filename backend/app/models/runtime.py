"""Small, bounded operational snapshots; no credentials or command output."""
from datetime import datetime
from sqlalchemy import Column, DateTime, ForeignKey, Integer, JSON, String
from app.database import Base


class RuntimeSample(Base):
    __tablename__ = 'runtime_samples'
    id = Column(Integer, primary_key=True)
    collected_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    metrics = Column(JSON, nullable=False)


class ServerSyncState(Base):
    __tablename__ = 'server_sync_states'
    server_id = Column(Integer, ForeignKey('frps_servers.id'), primary_key=True)
    attempted_at = Column(DateTime, nullable=False)
    succeeded_at = Column(DateTime)
    status = Column(String(20), nullable=False)
    message = Column(String(200), nullable=False)
    duration_ms = Column(Integer)


class ProxyProbe(Base):
    __tablename__ = 'proxy_probes'
    proxy_id = Column(Integer, ForeignKey('proxies.id'), primary_key=True)
    checked_at = Column(DateTime, nullable=False)
    address = Column(String(253), nullable=False)
    port = Column(Integer, nullable=False)
    status = Column(String(20), nullable=False)
    message = Column(String(200), nullable=False)
    duration_ms = Column(Integer, nullable=False)
