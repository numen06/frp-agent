"""应用配置管理"""

import os
from functools import lru_cache
from typing import Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """应用配置"""

    # 应用配置
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    app_debug: bool = False

    # 数据库配置
    database_url: str = "sqlite:///./data/frp_agent.db"

    # 认证配置
    auth_username: str = "admin"
    auth_password: str = "admin"

    # frps 默认配置
    default_frps_name: str = "默认服务器"
    default_frps_server_addr: str = "127.0.0.1"
    default_frps_server_port: int = 7000
    default_frps_api_base_url: str = "http://127.0.0.1/api"
    default_frps_auth_username: str = "admin"
    default_frps_auth_password: str = "admin"

    # 镜像预装 frps；开关及运行配置由管理页面保存在数据库。
    builtin_frps_binary: str = "frps"
    builtin_frps_dir: str = "data/builtin_frps"

    # 同步任务配置
    sync_interval_seconds: int = 1800  # 30分钟

    # 安装包配置
    packages_dir: str = "data/packages"
    github_api_token: str = ""
    github_download_accelerate_prefix: str = "https://gh-proxy.com/"
    github_download_accelerate_fallback_prefixes: str = "https://ghfast.top/"

    # SSH 凭据加密密钥（生产环境务必配置）
    ssh_credential_secret: str = ""

    # 原生 SSH 跳板服务
    ssh_gateway_enabled: bool = True
    ssh_gateway_host: str = "0.0.0.0"
    ssh_gateway_port: int = 2222
    ssh_gateway_host_key_path: str = "data/ssh_gateway_host_key"

    # Docker Engine API 兼容 HTTPS 网关（转发至 Portainer）
    docker_gateway_enabled: bool = True
    docker_gateway_host: str = "0.0.0.0"
    docker_gateway_port: int = 23750
    docker_gateway_tls_common_name: str = "localhost"
    docker_gateway_tls_cert_path: str = "data/docker_gateway_tls_cert.pem"
    docker_gateway_tls_key_path: str = "data/docker_gateway_tls_key.pem"
    docker_gateway_request_timeout: int = 300

    # 原生 mstsc RDP/TLS 网关；证书和公网地址配置完成后再启用。
    rdp_gateway_enabled: bool = False
    rdp_gateway_host: str = "0.0.0.0"
    rdp_gateway_port: int = 13389
    rdp_gateway_public_address: str = ""
    rdp_gateway_binary: str = "freerdp-proxy3"
    rdp_gateway_tls_cert_path: str = "data/rdp_gateway_cert.pem"
    rdp_gateway_tls_key_path: str = "data/rdp_gateway_key.pem"
    # 只有来自这些 CIDR 的请求才读取 X-Forwarded-For；空值不信任代理头。
    rdp_gateway_trusted_proxies: str = ""

    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"  # 忽略额外的环境变量


@lru_cache()
def get_settings() -> Settings:
    """获取配置单例"""
    return Settings()
