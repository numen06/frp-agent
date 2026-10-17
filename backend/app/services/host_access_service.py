"""主机授权判断、SSH/Docker 执行和审计辅助。"""
from __future__ import annotations

import json
import shlex
import ssl
import time
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from urllib.parse import quote

import httpx

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.api_key import ApiKey
from app.models.docker_credential import DockerCredential
from app.models.managed_host import HostAccessGrant, HostAuditLog, ManagedHost
from app.models.ssh_credential import SshCredential
from app.models.user import User
from app.services.credential_encryption import decrypt_secret
from app.services.ssh_client import CommandResult, build_ssh_client


PERMISSION_FIELDS = {
    "connect": "can_connect",
    "execute": "can_execute",
    "docker": "can_manage_docker",
}
AUDIT_TEXT_LIMIT = 16000


def actor_identity(user: User) -> Tuple[str, int, str]:
    if user.id < 0:
        key_id = -user.id
        return "api_key", key_id, f"API Key #{key_id}"
    return "user", user.id, user.username


def is_admin(user: User) -> bool:
    return user.id == 0 or (user.id > 0 and getattr(user, "role", "admin") == "admin")


def require_admin(user: User) -> None:
    if not is_admin(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="仅管理员可以执行此操作",
        )


def active_grant(
    db: Session, user: User, host_id: int, permission: str
) -> Optional[HostAccessGrant]:
    if is_admin(user):
        return None
    subject_type, subject_id, _ = actor_identity(user)
    grant = (
        db.query(HostAccessGrant)
        .filter(
            HostAccessGrant.host_id == host_id,
            HostAccessGrant.subject_type == subject_type,
            HostAccessGrant.subject_id == subject_id,
            HostAccessGrant.is_active.is_(True),
        )
        .first()
    )
    field = PERMISSION_FIELDS.get(permission)
    if not grant or grant.is_expired() or not field or not getattr(grant, field):
        return None
    return grant


def require_host_access(
    db: Session, user: User, host_id: int, permission: str
) -> ManagedHost:
    host = db.query(ManagedHost).filter(ManagedHost.id == host_id).first()
    if not host:
        raise HTTPException(status_code=404, detail="主机不存在")
    if not host.is_active and not is_admin(user):
        raise HTTPException(status_code=403, detail="主机已禁用")
    if not is_admin(user) and not active_grant(db, user, host_id, permission):
        raise HTTPException(status_code=403, detail=f"没有该主机的 {permission} 权限")
    return host


def permissions_for(db: Session, user: User, host_id: int) -> List[str]:
    if is_admin(user):
        return ["connect", "execute", "docker"]
    subject_type, subject_id, _ = actor_identity(user)
    grant = (
        db.query(HostAccessGrant)
        .filter(
            HostAccessGrant.host_id == host_id,
            HostAccessGrant.subject_type == subject_type,
            HostAccessGrant.subject_id == subject_id,
            HostAccessGrant.is_active.is_(True),
        )
        .first()
    )
    if not grant or grant.is_expired():
        return []
    return [
        name for name, field in PERMISSION_FIELDS.items() if getattr(grant, field)
    ]


def accessible_host_ids(db: Session, user: User) -> Optional[List[int]]:
    if is_admin(user):
        return None
    subject_type, subject_id, _ = actor_identity(user)
    now = datetime.utcnow()
    rows = (
        db.query(HostAccessGrant.host_id)
        .filter(
            HostAccessGrant.subject_type == subject_type,
            HostAccessGrant.subject_id == subject_id,
            HostAccessGrant.is_active.is_(True),
            (HostAccessGrant.expires_at.is_(None) | (HostAccessGrant.expires_at > now)),
        )
        .all()
    )
    return [row[0] for row in rows]


def resolve_subject_name(db: Session, subject_type: str, subject_id: int) -> str:
    if subject_type == "user":
        row = db.query(User).filter(User.id == subject_id).first()
        return row.username if row else f"已删除用户 #{subject_id}"
    row = db.query(ApiKey).filter(ApiKey.id == subject_id).first()
    return row.description if row else f"已删除 API Key #{subject_id}"


def validate_subject(db: Session, subject_type: str, subject_id: int) -> None:
    model = User if subject_type == "user" else ApiKey
    if not db.query(model).filter(model.id == subject_id).first():
        raise HTTPException(status_code=404, detail="授权主体不存在")


def build_host_client(host: ManagedHost, credential: SshCredential):
    password = decrypt_secret(credential.password_encrypted)
    private_key = decrypt_secret(credential.private_key_encrypted)
    passphrase = decrypt_secret(credential.passphrase_encrypted)
    if credential.auth_type == "password" and not password:
        raise ValueError("SSH 密码无法解密，请重新保存凭据")
    if credential.auth_type == "private_key" and not private_key:
        raise ValueError("SSH 私钥无法解密，请重新保存凭据")
    return build_ssh_client(
        credential.auth_type,
        password,
        private_key,
        passphrase,
        expected_host_key=host.host_key_fingerprint,
    )


def run_host_command(
    host: ManagedHost, command: str, timeout: int = 30, use_sudo: bool = False
) -> Tuple[CommandResult, int, Optional[str]]:
    if not host.credential:
        raise ValueError("主机未配置 SSH 凭据")
    if host.host_type != "ssh":
        raise ValueError("该资源不是 SSH 主机")
    client = build_host_client(host, host.credential)
    started = time.monotonic()
    try:
        client.connect(host.address, host.port, host.credential.username, timeout=15.0)
        fingerprint_getter = getattr(client, "get_server_fingerprint", None)
        fingerprint = fingerprint_getter() if fingerprint_getter else None
        if use_sudo:
            sudo_password = decrypt_secret(host.credential.sudo_password_encrypted)
            if not sudo_password:
                raise ValueError("该 SSH 凭据未配置 sudo 密码")
            result = client.exec_command(
                f"sudo -S -p '' -- sh -c {shlex.quote(command)}",
                timeout=float(timeout),
                stdin_data=f"{sudo_password}\n",
            )
        else:
            result = client.exec_command(command, timeout=float(timeout))
        duration_ms = int((time.monotonic() - started) * 1000)
        return result, duration_ms, fingerprint
    finally:
        client.close()


def portainer_proxy_request(
    host: ManagedHost,
    method: str,
    path: str,
    timeout: int = 30,
    *,
    body: Optional[bytes] = None,
    request_headers: Optional[Dict[str, str]] = None,
) -> Tuple[int, Dict[str, str], bytes, int]:
    credential: Optional[DockerCredential] = host.docker_credential
    if host.host_type != "docker":
        raise ValueError("该资源不是 Docker 主机")
    if not credential:
        raise ValueError("Docker 主机未配置 Portainer 凭据")
    if not host.docker_endpoint_id:
        raise ValueError("Docker 主机未配置 Portainer Endpoint ID")

    scheme = "https" if host.docker_use_tls else "http"
    base_url = (
        f"{host.address.rstrip('/')}/"
        if "://" in host.address
        else f"{scheme}://{host.address}:{host.port}/"
    )
    ca_cert = decrypt_secret(credential.ca_cert_encrypted)
    verify = (
        (ssl.create_default_context(cadata=ca_cert) if ca_cert else True)
        if host.docker_verify_tls
        else False
    )
    headers = {}
    username = None
    password = None

    if credential.auth_type == "api_key":
        api_key = decrypt_secret(credential.api_key_encrypted)
        if not api_key:
            raise ValueError("Portainer API Key 无法解密")
        headers["X-API-Key"] = api_key
    elif credential.auth_type == "password":
        password = decrypt_secret(credential.password_encrypted)
        if not credential.username or password is None:
            raise ValueError("Portainer 用户名/密码无法解密")
        username = credential.username
    else:
        raise ValueError(f"不支持的 Portainer 认证方式: {credential.auth_type}")

    started = time.monotonic()
    with httpx.Client(
        base_url=base_url,
        verify=verify,
        timeout=float(timeout),
        headers=headers,
    ) as client:
        if username is not None:
            auth_response = client.post(
                "/api/auth", json={"Username": username, "Password": password}
            )
            if auth_response.status_code != 200:
                duration_ms = int((time.monotonic() - started) * 1000)
                return (
                    auth_response.status_code,
                    dict(auth_response.headers),
                    auth_response.content,
                    duration_ms,
                )
            token = auth_response.json().get("jwt")
            if not token:
                raise ValueError("Portainer 登录响应未包含 JWT")
            client.headers["Authorization"] = f"Bearer {token}"
            response = client.request(
                method, path, content=body, headers=request_headers
            )
        else:
            response = client.request(
                method, path, content=body, headers=request_headers
            )
    duration_ms = int((time.monotonic() - started) * 1000)
    return (
        response.status_code,
        dict(response.headers),
        response.content,
        duration_ms,
    )


def _docker_request(
    host: ManagedHost, method: str, path: str, timeout: int = 30
) -> Tuple[CommandResult, int]:
    status_code, _, content, duration_ms = portainer_proxy_request(
        host, method, path, timeout
    )
    text_content = content.decode("utf-8", errors="replace")
    ok = 200 <= status_code < 300
    return (
        CommandResult(
            exit_code=0 if ok else 1,
            stdout=text_content if ok else "",
            stderr="" if ok else f"HTTP {status_code}: {text_content}",
        ),
        duration_ms,
    )


def test_docker_connection(host: ManagedHost, timeout: int = 20):
    return _docker_request(
        host, "GET", f"/api/endpoints/{host.docker_endpoint_id}", timeout
    )


def get_docker_version_info(host: ManagedHost, timeout: int = 20):
    """读取 Endpoint 对应 Docker Engine 的版本信息。"""
    result, duration_ms = _docker_request(
        host,
        "GET",
        f"/api/endpoints/{host.docker_endpoint_id}/docker/version",
        timeout,
    )
    if result.exit_code != 0:
        return None, duration_ms
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError:
        return None, duration_ms

    parts = []
    version = payload.get("Version")
    api_version = payload.get("ApiVersion")
    platform_name = (payload.get("Platform") or {}).get("Name")
    os_name = payload.get("Os")
    architecture = payload.get("Arch")
    if version:
        parts.append(f"Docker {version}")
    if api_version:
        parts.append(f"API {api_version}")
    if platform_name:
        parts.append(str(platform_name))
    elif os_name or architecture:
        parts.append("/".join(value for value in (os_name, architecture) if value))
    return (" | ".join(parts)[:500] or None), duration_ms


def list_docker_containers(host: ManagedHost, timeout: int = 30):
    result, duration_ms = _docker_request(
        host,
        "GET",
        f"/api/endpoints/{host.docker_endpoint_id}/docker/containers/json?all=true",
        timeout,
    )
    containers: List[Dict] = []
    if result.exit_code == 0:
        try:
            containers = json.loads(result.stdout)
        except json.JSONDecodeError as exc:
            result = CommandResult(1, "", f"Docker 返回了无效 JSON: {exc}")
    return result, duration_ms, containers


def run_docker_action(
    host: ManagedHost, action: str, container: str, timeout: int = 30
):
    encoded = quote(container, safe="")
    return _docker_request(
        host,
        "POST",
        f"/api/endpoints/{host.docker_endpoint_id}/docker/containers/{encoded}/{action}",
        timeout,
    )


def add_audit_log(
    db: Session,
    host: ManagedHost,
    user: User,
    action: str,
    status_value: str,
    client_ip: Optional[str],
    *,
    target: Optional[str] = None,
    command: Optional[str] = None,
    result: Optional[CommandResult] = None,
    duration_ms: Optional[int] = None,
    error: Optional[str] = None,
) -> HostAuditLog:
    actor_type, actor_id, actor_name = actor_identity(user)
    log = HostAuditLog(
        host_id=host.id,
        actor_type=actor_type,
        actor_id=actor_id,
        actor_name=actor_name,
        action=action,
        target=target,
        command=command,
        status=status_value,
        exit_code=result.exit_code if result else None,
        stdout=(result.stdout or "")[:AUDIT_TEXT_LIMIT] if result else None,
        stderr=(
            ((result.stderr if result else None) or error or "")[:AUDIT_TEXT_LIMIT]
        ),
        client_ip=client_ip,
        duration_ms=duration_ms,
    )
    db.add(log)
    db.commit()
    return log
