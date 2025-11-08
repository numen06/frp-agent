"""frps 服务器相关 schemas"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class FrpsServerCreate(BaseModel):
    """创建 frps 服务器请求"""
    name: str
    server_addr: str
    server_port: int = 7000
    api_base_url: str
    auth_username: str
    auth_password: str
    auth_token: Optional[str] = None


class FrpsServerUpdate(BaseModel):
    """更新 frps 服务器请求"""
    name: Optional[str] = None
    server_addr: Optional[str] = None
    server_port: Optional[int] = None
    api_base_url: Optional[str] = None
    auth_username: Optional[str] = None
    auth_password: Optional[str] = None
    auth_token: Optional[str] = None


class FrpsServerResponse(BaseModel):
    """frps 服务器响应"""
    id: int
    name: str
    server_addr: str
    server_port: int
    api_base_url: str
    auth_username: str
    auth_token: Optional[str] = None
    is_active: bool
    last_test_status: str = "unknown"
    last_test_time: Optional[datetime] = None
    last_test_message: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True

