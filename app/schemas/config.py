"""配置生成相关 schemas"""
from typing import List, Optional
from pydantic import BaseModel


class ProxyConfig(BaseModel):
    """单个代理配置"""
    name: str
    type: str = "tcp"
    local_ip: str = "127.0.0.1"
    local_port: int
    remote_port: Optional[int] = None
    custom_domains: Optional[List[str]] = None
    subdomain: Optional[str] = None


class ConfigGenerateRequest(BaseModel):
    """生成配置请求"""
    frps_server_id: int
    proxies: List[ProxyConfig]
    user_token: Optional[str] = None
    use_encryption: bool = False
    use_compression: bool = False


class ConfigGenerateResponse(BaseModel):
    """生成配置响应"""
    config_content: str
    filename: str
    startup_script: Optional[str] = None

