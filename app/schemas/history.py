"""历史记录相关 schemas"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class ProxyHistoryResponse(BaseModel):
    """代理历史记录响应"""
    id: int
    frps_server_id: int
    proxy_name: str
    action: str
    timestamp: datetime
    details: Optional[str]
    
    class Config:
        from_attributes = True

