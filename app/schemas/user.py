"""用户相关 schemas"""
from datetime import datetime
from pydantic import BaseModel


class UserCreate(BaseModel):
    """创建用户请求"""
    username: str
    password: str


class UserResponse(BaseModel):
    """用户响应"""
    id: int
    username: str
    created_at: datetime
    
    class Config:
        from_attributes = True

