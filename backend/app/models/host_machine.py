"""A machine owns independent protocol connection profiles."""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from app.database import Base


class HostMachine(Base):
    __tablename__ = 'host_machines'
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False, index=True)
    description = Column(Text, nullable=True)
    frps_server_id = Column(Integer, ForeignKey('frps_servers.id'), nullable=True)
    group_name = Column(String(50), nullable=True, index=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
