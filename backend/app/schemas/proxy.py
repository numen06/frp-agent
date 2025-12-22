"""代理相关 schemas"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class ProxyCreate(BaseModel):
    """创建代理请求"""
    frps_server_id: int
    name: str
    group_name: Optional[str] = None  # 可选，如果不提供则自动从name中解析
    proxy_type: str = "tcp"  # tcp, udp, http, https, stcp, xtcp
    remote_port: Optional[int] = None
    local_ip: str = "127.0.0.1"
    local_port: int = 0  # 默认为0，如果为0则自动从名称识别
    client_name: Optional[str] = None


class ProxyUpdate(BaseModel):
    """更新代理请求"""
    name: Optional[str] = None
    group_name: Optional[str] = None
    proxy_type: Optional[str] = None
    remote_port: Optional[int] = None
    local_ip: Optional[str] = None
    local_port: Optional[int] = None
    client_name: Optional[str] = None
    status: Optional[str] = None


class ProxyResponse(BaseModel):
    """代理响应"""
    id: int
    frps_server_id: int
    name: str
    group_name: Optional[str]
    proxy_type: str
    remote_port: Optional[int]
    local_ip: str
    local_port: int
    client_name: Optional[str]
    status: str
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

