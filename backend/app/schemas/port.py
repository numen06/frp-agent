"""端口相关 schemas"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class PortAllocateRequest(BaseModel):
    """分配端口请求"""
    frps_server_id: int
    port: int
    allocated_to: str


class PortReleaseRequest(BaseModel):
    """释放端口请求"""
    frps_server_id: int
    port: int


class PortAllocationResponse(BaseModel):
    """端口分配响应"""
    id: int
    frps_server_id: int
    port: int
    is_allocated: bool
    allocated_to: Optional[str]
    allocated_at: datetime
    
    class Config:
        from_attributes = True

