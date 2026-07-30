"""主机管理 API schemas。"""
import base64
import binascii
from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, Field, field_validator


def _normalize_ssh_public_key(value: Optional[str]) -> Optional[str]:
    if value is None or not value.strip():
        return None
    parts = value.strip().split()
    if len(parts) < 2 or not (
        parts[0].startswith("ssh-")
        or parts[0].startswith("ecdsa-")
        or parts[0].startswith("sk-")
    ):
        raise ValueError("请输入 OpenSSH 公钥，例如 ssh-ed25519 AAAA...")
    try:
        base64.b64decode(parts[1], validate=True)
    except (ValueError, binascii.Error):
        raise ValueError("SSH 公钥内容无效")
    return f"{parts[0]} {parts[1]}"


class ManagedHostCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    address: str = Field(..., min_length=1, max_length=255)
    port: int = Field(22, ge=1, le=65535)
    host_type: Literal["ssh", "docker"] = "ssh"
    credential_id: Optional[int] = Field(None, gt=0)
    docker_credential_id: Optional[int] = Field(None, gt=0)
    docker_use_tls: bool = True
    docker_verify_tls: bool = True
    docker_endpoint_id: Optional[int] = Field(None, gt=0)
    description: Optional[str] = Field(None, max_length=2000)
    tags: Optional[str] = Field(None, max_length=500)
    is_active: bool = True
    host_key_fingerprint: Optional[str] = Field(None, max_length=100)

    @field_validator("name", "address")
    @classmethod
    def strip_required(cls, value):
        value = value.strip()
        if not value:
            raise ValueError("不能为空")
        return value

    @field_validator("host_key_fingerprint")
    @classmethod
    def validate_fingerprint(cls, value):
        if value is None or not value.strip():
            return None
        value = value.strip()
        if not value.startswith("SHA256:"):
            raise ValueError("主机指纹必须使用 SHA256: 格式")
        return value


class ManagedHostUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    address: Optional[str] = Field(None, min_length=1, max_length=255)
    port: Optional[int] = Field(None, ge=1, le=65535)
    host_type: Optional[Literal["ssh", "docker"]] = None
    credential_id: Optional[int] = Field(None, gt=0)
    docker_credential_id: Optional[int] = Field(None, gt=0)
    docker_use_tls: Optional[bool] = None
    docker_verify_tls: Optional[bool] = None
    docker_endpoint_id: Optional[int] = Field(None, gt=0)
    description: Optional[str] = Field(None, max_length=2000)
    tags: Optional[str] = Field(None, max_length=500)
    is_active: Optional[bool] = None
    host_key_fingerprint: Optional[str] = Field(None, max_length=100)


class ManagedHostResponse(BaseModel):
    id: int
    name: str
    address: str
    port: int
    host_type: str
    credential_id: Optional[int]
    docker_credential_id: Optional[int]
    credential_name: str
    credential_username: str
    credential_kind: str
    docker_use_tls: bool
    docker_verify_tls: bool
    docker_endpoint_id: Optional[int]
    description: Optional[str]
    tags: Optional[str]
    is_active: bool
    host_key_fingerprint: Optional[str]
    last_status: str
    last_checked_at: Optional[datetime]
    last_message: Optional[str]
    version_info: Optional[str]
    permissions: List[str] = Field(default_factory=list)
    can_manage: bool = False
    created_at: datetime
    updated_at: datetime


class HostGrantCreate(BaseModel):
    host_id: int = Field(..., gt=0)
    subject_type: Literal["user", "api_key"]
    subject_id: int = Field(..., gt=0)
    can_connect: bool = True
    can_execute: bool = False
    can_manage_docker: bool = False
    is_active: bool = True
    expires_at: Optional[datetime] = None


class HostGrantUpdate(BaseModel):
    can_connect: Optional[bool] = None
    can_execute: Optional[bool] = None
    can_manage_docker: Optional[bool] = None
    is_active: Optional[bool] = None
    expires_at: Optional[datetime] = None


class HostGrantResponse(BaseModel):
    id: int
    host_id: int
    host_name: str
    subject_type: str
    subject_id: int
    subject_name: str
    can_connect: bool
    can_execute: bool
    can_manage_docker: bool
    is_active: bool
    expires_at: Optional[datetime]
    is_expired: bool
    created_at: datetime
    updated_at: datetime


class HostCommandRequest(BaseModel):
    command: str = Field(..., min_length=1, max_length=4000)
    timeout: int = Field(30, ge=1, le=120)
    use_sudo: bool = False

    @field_validator("command")
    @classmethod
    def strip_command(cls, value):
        value = value.strip()
        if not value:
            raise ValueError("命令不能为空")
        return value


class DockerActionRequest(BaseModel):
    action: Literal["start", "stop", "restart"]
    container: str = Field(..., min_length=1, max_length=128, pattern=r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")
    timeout: int = Field(30, ge=1, le=120)


class HostOperationResponse(BaseModel):
    success: bool
    exit_code: Optional[int] = None
    stdout: str = ""
    stderr: str = ""
    duration_ms: int
    fingerprint: Optional[str] = None
    version_info: Optional[str] = None


class HostContextResponse(BaseModel):
    actor_type: str
    actor_id: int
    actor_name: str
    is_admin: bool


class AccessSubjectResponse(BaseModel):
    subject_type: str
    id: int
    name: str
    description: Optional[str] = None
    is_active: bool
    role: Optional[str] = None
    has_ssh_public_key: bool = False


class ManagedUserCreate(BaseModel):
    username: str = Field(..., min_length=2, max_length=50, pattern=r"^[A-Za-z0-9_.-]+$")
    password: str = Field(..., min_length=8, max_length=128)
    role: Literal["admin", "user"] = "user"
    ssh_public_key: Optional[str] = Field(None, max_length=16384)

    @field_validator("ssh_public_key")
    @classmethod
    def validate_ssh_public_key(cls, value):
        return _normalize_ssh_public_key(value)


class ManagedUserUpdate(BaseModel):
    password: Optional[str] = Field(None, min_length=8, max_length=128)
    role: Optional[Literal["admin", "user"]] = None
    is_active: Optional[bool] = None
    ssh_public_key: Optional[str] = Field(None, max_length=16384)

    @field_validator("ssh_public_key")
    @classmethod
    def validate_ssh_public_key(cls, value):
        return _normalize_ssh_public_key(value)


class HostAuditResponse(BaseModel):
    id: int
    host_id: int
    host_name: str
    actor_type: str
    actor_id: int
    actor_name: str
    action: str
    target: Optional[str]
    command: Optional[str]
    status: str
    exit_code: Optional[int]
    stdout: Optional[str]
    stderr: Optional[str]
    client_ip: Optional[str]
    duration_ms: Optional[int]
    created_at: datetime


class DockerCredentialCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    auth_type: Literal["api_key", "password"]
    username: Optional[str] = Field(None, max_length=100)
    password: Optional[str] = None
    api_key: Optional[str] = None
    ca_cert: Optional[str] = None


class DockerCredentialUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    auth_type: Optional[Literal["api_key", "password"]] = None
    username: Optional[str] = Field(None, max_length=100)
    password: Optional[str] = None
    api_key: Optional[str] = None
    ca_cert: Optional[str] = None


class DockerCredentialResponse(BaseModel):
    id: int
    name: str
    auth_type: str
    username: Optional[str]
    has_password: bool
    has_api_key: bool
    has_ca_cert: bool
    created_at: datetime
    updated_at: datetime
