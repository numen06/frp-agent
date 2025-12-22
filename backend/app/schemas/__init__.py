"""Pydantic schemas"""
from app.schemas.user import UserCreate, UserResponse
from app.schemas.frps_server import FrpsServerCreate, FrpsServerUpdate, FrpsServerResponse
from app.schemas.proxy import ProxyCreate, ProxyUpdate, ProxyResponse
from app.schemas.port import PortAllocationResponse, PortAllocateRequest
from app.schemas.config import ConfigGenerateRequest, ConfigGenerateResponse
from app.schemas.history import ProxyHistoryResponse

__all__ = [
    "UserCreate",
    "UserResponse",
    "FrpsServerCreate",
    "FrpsServerUpdate",
    "FrpsServerResponse",
    "ProxyCreate",
    "ProxyUpdate",
    "ProxyResponse",
    "PortAllocationResponse",
    "PortAllocateRequest",
    "ConfigGenerateRequest",
    "ConfigGenerateResponse",
    "ProxyHistoryResponse",
]

