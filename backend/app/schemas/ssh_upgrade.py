"""SSH 升级相关 schemas"""
from datetime import datetime
from typing import List, Literal, Optional
from pydantic import BaseModel, Field


class SshUpgradeRequest(BaseModel):
    credential_id: int
    install_path: str = Field(default="/opt/frp", max_length=500)
    verify_mode: Literal["agent_callback", "backend_poll", "skip"] = "agent_callback"
    verify_attempts: int = Field(default=18, ge=1, le=120)
    verify_interval: int = Field(default=5, ge=1, le=60)
    skip_remote_verify: bool = False


class GroupSshUpgradeRequest(SshUpgradeRequest):
    proxy_ids: Optional[List[int]] = None


class ProxySshStateResponse(BaseModel):
    proxy_id: int
    credential_id: Optional[int] = None
    is_ssh_candidate: bool = False
    reachable: Optional[bool] = None
    platform: Optional[str] = None
    install_path: Optional[str] = None
    frpc_bin_path: Optional[str] = None
    config_path: Optional[str] = None
    config_format: Optional[str] = None
    has_ini: bool = False
    has_toml: bool = False
    service_name: str = "frpc"
    current_version: Optional[str] = None
    target_version: Optional[str] = None
    target_package_id: Optional[int] = None
    upgradeable: bool = False
    rollback_capable: bool = False
    status: str
    message: Optional[str] = None
    last_scanned_at: Optional[datetime] = None
    last_upgraded_at: Optional[datetime] = None
    proxy_name: Optional[str] = None
    ssh_target: Optional[str] = None  # host:port for SSH connection


class VerifyResponse(BaseModel):
    ok: bool
    online: bool
    client_version: Optional[str] = None
    expected_version: Optional[str] = None
    message: Optional[str] = None


class ClientUpgradeJobResponse(BaseModel):
    id: int
    job_type: str
    scope_type: str
    frps_server_id: Optional[int] = None
    group_name: Optional[str] = None
    proxy_id: Optional[int] = None
    credential_id: Optional[int] = None
    status: str
    total_count: int
    success_count: int
    failed_count: int
    skipped_count: int
    summary: Optional[str] = None
    result_json: Optional[str] = None
    error_message: Optional[str] = None
    created_at: datetime
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None

    class Config:
        from_attributes = True
