"""API Key 相关 schemas"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, validator


class ApiKeyCreate(BaseModel):
    """创建 API Key 请求"""
    description: str = Field(..., min_length=1, max_length=200, description="密钥描述（必须）")
    expires_at: Optional[datetime] = Field(None, description="过期时间（可选）")
    
    @validator('description')
    def validate_description(cls, v):
        if not v or not v.strip():
            raise ValueError('描述不能为空')
        return v.strip()


class ApiKeyResponse(BaseModel):
    """API Key 响应"""
    id: int
    key: str  # 只返回前8位和后4位，中间用*代替
    description: str
    expires_at: Optional[datetime]
    is_active: bool
    created_at: datetime
    last_used_at: Optional[datetime]
    is_expired: bool  # 是否已过期
    
    class Config:
        from_attributes = True


class ApiKeyCreateResponse(BaseModel):
    """创建 API Key 响应（包含完整密钥）"""
    id: int
    key: str  # 完整密钥（只在创建时返回一次）
    description: str
    expires_at: Optional[datetime]
    is_active: bool
    created_at: datetime
    warning: str = "请妥善保管此密钥，创建后将无法再次查看完整密钥"


class ApiKeyUpdate(BaseModel):
    """更新 API Key 请求"""
    description: Optional[str] = Field(None, min_length=1, max_length=200)
    expires_at: Optional[datetime] = None
    is_active: Optional[bool] = None


class ApiKeyFullKeyResponse(BaseModel):
    """获取完整密钥响应"""
    id: int
    key: str  # 完整密钥
    description: str

