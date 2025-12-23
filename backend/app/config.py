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

    # 同步任务配置
    sync_interval_seconds: int = 1800  # 30分钟

    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"  # 忽略额外的环境变量


@lru_cache()
def get_settings() -> Settings:
    """获取配置单例"""
    return Settings()
