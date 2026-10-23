"""主机管理、授权、远程操作与审计 API。"""
from datetime import datetime, timedelta, timezone
import hmac
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
import os
import json
import re
from urllib.parse import urlsplit, urlunsplit
from sqlalchemy.exc import IntegrityError
from sqlalchemy import literal, func, insert, select, cast, String, case
from sqlalchemy.orm import Session, joinedload

from app.auth import get_current_user, get_password_hash
from app.database import get_db
from app.pagination import Page, PageParams, paginate, search_query
from app.models.api_key import ApiKey
from app.models.docker_credential import DockerCredential
from app.models.managed_host import HostAccessGrant, HostAuditLog, ManagedHost
from app.models.ssh_credential import SshCredential
from app.models.user import User
from app.schemas.managed_host import (
    AccessSubjectResponse,
    DockerActionRequest,
    HostAuditResponse,
    HostAuditDeleteRequest,
    HostAuditCleanupRequest,
    HostCommandRequest,
    HostContextResponse,
    HostGrantCreate,
    HostGrantResponse,
    HostGrantUpdate,
    HostOperationResponse,
    ManagedHostCreate,
    ManagedHostResponse,
    ManagedHostUpdate,
    ManagedUserCreate,
    ManagedUserUpdate,
    RdpGatewayAuthorization,
    RdpFingerprintRequest,
)
from app.services.host_access_service import (
    accessible_host_ids,
    actor_identity,
    add_audit_log,
    get_docker_version_info,
    is_admin,
    list_docker_containers,
    permissions_for,
    require_admin,
    require_host_access,
    resolve_subject_name,
    run_docker_action,
    run_host_command,
    test_docker_connection,
    validate_subject,
)
from app.services.ssh_gateway_service import ssh_gateway_service
from app.services.docker_gateway_service import (
    docker_gateway_certificate_fingerprint,
    docker_gateway_service,
    issue_docker_client_certificate,
)
from app.config import get_settings
from app.services.rdp_gateway_service import (
    rdp_gateway_service, rdp_client_ip, validate_rdp_address, test_rdp_connection,
    require_secure_rdp_download,
    probe_rdp_fingerprint,
)

router = APIRouter(prefix="/api/managed-hosts", tags=["主机管理"])


def _client_ip(request: Request) -> Optional[str]:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",", 1)[0].strip()
    return request.client.host if request.client else None


def _get_credential(db: Session, credential_id: int) -> SshCredential:
    credential = (
        db.query(SshCredential).filter(SshCredential.id == credential_id).first()
    )
    if not credential:
        raise HTTPException(status_code=404, detail="SSH 凭据不存在")
    return credential


def _get_docker_credential(db: Session, credential_id: int) -> DockerCredential:
    credential = (
        db.query(DockerCredential)
        .filter(DockerCredential.id == credential_id)
        .first()
    )
    if not credential:
        raise HTTPException(status_code=404, detail="Docker 凭据不存在")
    return credential


def _validate_host_credentials(db: Session, values: dict) -> None:
    if values["host_type"] == "ssh":
        if not values.get("credential_id"):
            raise HTTPException(status_code=400, detail="SSH 主机必须配置 SSH 凭据")
        _get_credential(db, values["credential_id"])
        values["docker_credential_id"] = None
        values["docker_endpoint_id"] = None
    elif values["host_type"] == "docker":
        if not values.get("docker_credential_id"):
            raise HTTPException(status_code=400, detail="Docker 主机必须配置 Docker 凭据")
        _get_docker_credential(db, values["docker_credential_id"])
        values["credential_id"] = None
        values["host_key_fingerprint"] = None
        if not values.get("docker_endpoint_id"):
            raise HTTPException(
                status_code=400, detail="Docker 主机必须配置 Portainer Endpoint ID"
            )
        address = values.get("address", "").strip().rstrip("/")
        if "://" in address:
            try:
                parsed = urlsplit(address)
                port = parsed.port
            except ValueError:
                raise HTTPException(status_code=400, detail="Portainer URL 端口无效")
            if (
                parsed.scheme not in {"http", "https"}
                or not parsed.hostname
                or parsed.username
                or parsed.password
                or parsed.query
                or parsed.fragment
            ):
                raise HTTPException(status_code=400, detail="Portainer URL 格式无效")
            values["address"] = urlunsplit(
                (parsed.scheme, parsed.netloc, parsed.path.rstrip("/"), "", "")
            )
            values["port"] = port or (443 if parsed.scheme == "https" else 80)
            values["docker_use_tls"] = parsed.scheme == "https"
            if parsed.scheme == "http":
                values["docker_verify_tls"] = False
        elif "/" in address:
            raise HTTPException(
                status_code=400,
                detail="Portainer 含路径时请填写完整 URL，例如 http://host/docker/",
            )
    elif values["host_type"] == "rdp":
        values["address"] = validate_rdp_address(values["address"])
        if not values.get("credential_id"):
            raise HTTPException(status_code=400, detail="RDP 主机必须绑定 Windows 密码凭据")
        credential = _get_credential(db, values["credential_id"])
        if credential.auth_type != "password":
            raise HTTPException(status_code=400, detail="RDP 不支持私钥凭据，请选择 Windows 密码凭据")
        pin = (values.get("host_key_fingerprint") or "").strip()
        if not pin:
            pin = probe_rdp_fingerprint(values["address"], values["port"])
        if not re.fullmatch(r"SHA256:[0-9a-fA-F]{64}", pin):
            raise HTTPException(status_code=400, detail="请填写 RDP 证书的 SHA256:十六进制指纹")
        values["host_key_fingerprint"] = "SHA256:" + pin.removeprefix("SHA256:").lower()
        values["docker_credential_id"] = None
        values["docker_endpoint_id"] = None
    else:
        raise HTTPException(status_code=400, detail="不支持的主机类型")
    if values["host_type"] == "ssh" and "://" in values.get("address", ""):
        raise HTTPException(status_code=400, detail="地址只填写主机名或 IP，不要包含协议")


def _host_response(
    db: Session, host: ManagedHost, current_user: User
) -> ManagedHostResponse:
    credential = host.credential if host.host_type in {"ssh", "rdp"} else host.docker_credential
    return ManagedHostResponse(
        id=host.id,
        name=host.name,
        address=host.address,
        port=host.port,
        host_type=host.host_type,
        credential_id=host.credential_id,
        docker_credential_id=host.docker_credential_id,
        credential_name=credential.name if credential else "未配置凭据",
        credential_username=(credential.username or "") if credential else "",
        credential_kind={"ssh": "SSH", "docker": "Docker", "rdp": "RDP"}[host.host_type],
        docker_use_tls=host.docker_use_tls,
        docker_verify_tls=host.docker_verify_tls,
        docker_endpoint_id=host.docker_endpoint_id,
        description=host.description,
        tags=host.tags,
        is_active=host.is_active,
        host_key_fingerprint=host.host_key_fingerprint,
        last_status=host.last_status,
        last_checked_at=host.last_checked_at,
        last_message=host.last_message,
        version_info=host.version_info,
        permissions=permissions_for(db, current_user, host.id),
        can_manage=is_admin(current_user),
        created_at=host.created_at,
        updated_at=host.updated_at,
    )


def _grant_response(db: Session, grant: HostAccessGrant) -> HostGrantResponse:
    return HostGrantResponse(
        id=grant.id,
        host_id=grant.host_id,
        host_name=grant.host.name if grant.host else f"主机 #{grant.host_id}",
        subject_type=grant.subject_type,
        subject_id=grant.subject_id,
        subject_name=resolve_subject_name(db, grant.subject_type, grant.subject_id),
        can_connect=grant.can_connect,
        can_execute=grant.can_execute,
        can_manage_docker=grant.can_manage_docker,
        is_active=grant.is_active,
        expires_at=grant.expires_at,
        is_expired=grant.is_expired(),
        created_at=grant.created_at,
        updated_at=grant.updated_at,
    )


@router.get("/context", response_model=HostContextResponse)
def get_context(current_user: User = Depends(get_current_user)):
    actor_type, actor_id, actor_name = actor_identity(current_user)
    return HostContextResponse(
        actor_type=actor_type,
        actor_id=actor_id,
        actor_name=actor_name,
        is_admin=is_admin(current_user),
    )


@router.get("/gateway/info")
def get_gateway_info(current_user: User = Depends(get_current_user)):
    settings = get_settings()
    return {
        "enabled": settings.ssh_gateway_enabled,
        "running": ssh_gateway_service.running,
        "listen_host": settings.ssh_gateway_host,
        "port": settings.ssh_gateway_port,
        "host_key_fingerprint": ssh_gateway_service.host_key_fingerprint,
        "user_login_format": "<系统用户>#<SSH主机名>",
        "user_auth_methods": ["password", "publickey"],
        "api_key_login_format": "<SSH主机名>",
        "rdp_gateway": {
            "enabled": settings.rdp_gateway_enabled,
            "running": rdp_gateway_service.running,
            "port": settings.rdp_gateway_port,
            "public_address": settings.rdp_gateway_public_address,
            "user_login_format": "<系统用户>#<RDP主机名>",
            "api_key_login_format": "<RDP主机名>",
        },
        "docker_gateway": {
            "enabled": settings.docker_gateway_enabled,
            "running": docker_gateway_service.running,
            "listen_host": settings.docker_gateway_host,
            "port": settings.docker_gateway_port,
            "tls_common_name": settings.docker_gateway_tls_common_name,
            "certificate_fingerprint": docker_gateway_certificate_fingerprint(),
            "client_certificate_available": bool(
                current_user.id > 0 and current_user.ssh_public_key
            ),
            "user_login_format": "<系统用户>#<Docker主机名>",
            "api_key_login_format": "<Docker主机名>",
        },
    }


@router.post("/rdp/fingerprint")
def get_rdp_fingerprint(
    body: RdpFingerprintRequest,
    current_user: User = Depends(get_current_user),
):
    require_admin(current_user)
    return Response(json.dumps({"fingerprint": probe_rdp_fingerprint(body.address, body.port)}),
                    media_type="application/json", headers={"Cache-Control": "no-store"})


@router.post("/gateway/rdp/authorize")
def authorize_rdp_gateway(
    body: RdpGatewayAuthorization,
    request: Request,
    db: Session = Depends(get_db),
):
    # This is a local child-process callback, never a browser-facing auth API.
    peer = request.client.host if request.client else ""
    supplied = request.headers.get("x-rdp-internal-secret", "")
    if (peer not in {"127.0.0.1", "::1", "::ffff:127.0.0.1"}
            or not get_settings().rdp_gateway_enabled
            or not hmac.compare_digest(supplied, rdp_gateway_service.internal_secret)):
        raise HTTPException(status_code=403, detail="禁止访问 RDP 内部接口")
    result = rdp_gateway_service.authorize(db, body.connection_port, body.username, body.password, body.phase, body.domain)
    return Response(json.dumps(result), media_type="application/json", headers={"Cache-Control": "no-store"})


@router.post("/{host_id}/rdp-file")
def download_rdp_file(
    host_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    host = require_host_access(db, current_user, host_id, "connect")
    require_secure_rdp_download(request)
    content = rdp_gateway_service.issue_file(db, current_user, host, rdp_client_ip(request))
    return Response(content, media_type="application/x-rdp", headers={
        "Content-Disposition": f'attachment; filename="frp-agent-rdp-{host.id}.rdp"',
        "Cache-Control": "no-store", "X-Content-Type-Options": "nosniff",
    })


@router.get("/gateway/docker-ca")
def get_docker_gateway_ca(current_user: User = Depends(get_current_user)):
    cert_path = os.path.abspath(get_settings().docker_gateway_tls_cert_path)
    if not os.path.exists(cert_path):
        raise HTTPException(status_code=404, detail="Docker 网关证书尚未生成")
    with open(cert_path, "rb") as cert_file:
        content = cert_file.read()
    return Response(
        content=content,
        media_type="application/x-pem-file",
        headers={
            "Content-Disposition": 'attachment; filename="frp-agent-docker-gateway-ca.pem"'
        },
    )


@router.get("/{host_id}/docker-client-cert")
def get_docker_client_certificate(
    host_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    host = require_host_access(db, current_user, host_id, "docker")
    try:
        content = issue_docker_client_certificate(current_user, host)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return Response(
        content=content,
        media_type="application/x-pem-file",
        headers={
            "Content-Disposition": (
                f'attachment; filename="frp-agent-docker-client-{host.id}.pem"'
            )
        },
    )


@router.get("", response_model=List[ManagedHostResponse] | Page[ManagedHostResponse])
def list_hosts(
    paging: PageParams = Depends(),
    host_id: Optional[int] = Query(None, gt=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(ManagedHost).options(joinedload(ManagedHost.credential), joinedload(ManagedHost.docker_credential)).order_by(ManagedHost.id.desc())
    if not is_admin(current_user):
        actor_type, actor_id, _ = actor_identity(current_user)
        allowed = db.query(HostAccessGrant.host_id).filter(
            HostAccessGrant.subject_type == actor_type,
            HostAccessGrant.subject_id == actor_id,
            HostAccessGrant.is_active.is_(True),
            HostAccessGrant.expires_at.is_(None) | (HostAccessGrant.expires_at > datetime.utcnow()),
        )
        query = query.filter(ManagedHost.id.in_(allowed), ManagedHost.is_active.is_(True))
    if host_id:
        query = query.filter(ManagedHost.id == host_id)
    query = search_query(query, paging.search, ManagedHost.name, ManagedHost.address, ManagedHost.tags)
    return paginate(query, paging, lambda row: _host_response(db, row, current_user))


@router.post("", response_model=ManagedHostResponse, status_code=status.HTTP_201_CREATED)
def create_host(
    body: ManagedHostCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_admin(current_user)
    values = body.model_dump()
    _validate_host_credentials(db, values)
    host = ManagedHost(
        **values,
        created_by_user_id=current_user.id if current_user.id > 0 else None,
    )
    db.add(host)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="主机名称已存在")
    db.refresh(host)
    return _host_response(db, host, current_user)


@router.put("/{host_id}", response_model=ManagedHostResponse)
def update_host(
    host_id: int,
    body: ManagedHostUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_admin(current_user)
    host = db.query(ManagedHost).filter(ManagedHost.id == host_id).first()
    if not host:
        raise HTTPException(status_code=404, detail="主机不存在")
    values = body.model_dump(exclude_unset=True)
    effective = {
        "host_type": values.get("host_type", host.host_type),
        "credential_id": values.get("credential_id", host.credential_id),
        "docker_credential_id": values.get(
            "docker_credential_id", host.docker_credential_id
        ),
        "address": values.get("address", host.address),
        "port": values.get("port", host.port),
        "docker_use_tls": values.get("docker_use_tls", host.docker_use_tls),
        "docker_verify_tls": values.get(
            "docker_verify_tls", host.docker_verify_tls
        ),
        "host_key_fingerprint": values.get(
            "host_key_fingerprint", host.host_key_fingerprint
        ),
        "docker_endpoint_id": values.get(
            "docker_endpoint_id", host.docker_endpoint_id
        ),
    }
    if (host.host_type == effective["host_type"] == "rdp" and host.host_key_fingerprint
            and not effective["host_key_fingerprint"]):
        effective["host_key_fingerprint"] = host.host_key_fingerprint
    _validate_host_credentials(db, effective)
    values.update(
        {
            "credential_id": effective["credential_id"],
            "docker_credential_id": effective["docker_credential_id"],
            "host_key_fingerprint": effective["host_key_fingerprint"],
            "docker_endpoint_id": effective["docker_endpoint_id"],
            "address": effective["address"],
            "port": effective["port"],
            "docker_use_tls": effective["docker_use_tls"],
            "docker_verify_tls": effective["docker_verify_tls"],
        }
    )
    if "name" in values:
        values["name"] = values["name"].strip()
    if "address" in values:
        values["address"] = values["address"].strip()
    for field, value in values.items():
        setattr(host, field, value)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="主机名称已存在")
    db.refresh(host)
    return _host_response(db, host, current_user)


@router.delete("/{host_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_host(
    host_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_admin(current_user)
    host = db.query(ManagedHost).filter(ManagedHost.id == host_id).first()
    if not host:
        raise HTTPException(status_code=404, detail="主机不存在")
    db.delete(host)
    db.commit()


@router.post("/{host_id}/test", response_model=HostOperationResponse)
def test_host(
    host_id: int,
    request: Request,
    save_fingerprint: bool = Query(
        True, description="首次连接时以 TOFU 方式保存 SSH 主机指纹"
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    host = require_host_access(db, current_user, host_id, "connect")
    try:
        version_info = None
        if host.host_type == "ssh":
            result, duration_ms, fingerprint = run_host_command(
                host,
                (
                    "if [ -r /etc/os-release ]; then "
                    ". /etc/os-release; "
                    "printf '%s' \"${PRETTY_NAME:-${NAME:-Linux}}\"; "
                    "else uname -s; fi; "
                    "printf ' | Kernel '; uname -r; "
                    "printf ' | '; uname -m"
                ),
                20,
            )
            if result.exit_code == 0:
                version_info = " ".join(result.stdout.split())[:500] or None
        elif host.host_type == "rdp":
            result, duration_ms = test_rdp_connection(host)
            fingerprint = None
        else:
            result, duration_ms = test_docker_connection(host, 20)
            fingerprint = None
            if result.exit_code == 0:
                version_traffic = {}
                version_info, version_duration_ms = get_docker_version_info(host, 20, version_traffic)
                duration_ms += version_duration_ms
                if result.bytes_sent is not None and version_traffic.get("bytes_sent") is not None:
                    result.bytes_sent += version_traffic["bytes_sent"]
                if result.bytes_received is not None and version_traffic.get("bytes_received") is not None:
                    result.bytes_received += version_traffic["bytes_received"]
        success = result.exit_code == 0
        host.last_status = "online" if success else "error"
        host.last_checked_at = datetime.utcnow()
        host.last_message = (
            f"{ {'ssh': 'SSH', 'docker': 'Portainer API', 'rdp': 'RDP TLS/证书'}[host.host_type]} 连接成功"
            if success
            else (result.stderr or "连接成功，但测试失败")
        )[:500]
        if success and version_info:
            host.version_info = version_info
        if (
            host.host_type == "ssh"
            and save_fingerprint
            and not host.host_key_fingerprint
            and fingerprint
        ):
            host.host_key_fingerprint = fingerprint
        db.commit()
        add_audit_log(
            db,
            host,
            current_user,
            "connection_test",
            "success" if success else "failed",
            _client_ip(request),
            result=result,
            duration_ms=duration_ms,
        )
        return HostOperationResponse(
            success=success,
            exit_code=result.exit_code,
            stdout=result.stdout,
            stderr=result.stderr,
            duration_ms=duration_ms,
            fingerprint=fingerprint,
            version_info=host.version_info if success else None,
        )
    except Exception as exc:
        db.rollback()
        host.last_status = "offline"
        host.last_checked_at = datetime.utcnow()
        host.last_message = str(exc)[:500]
        db.commit()
        add_audit_log(
            db,
            host,
            current_user,
            "connection_test",
            "failed",
            _client_ip(request),
            error=str(exc),
        )
        raise HTTPException(status_code=502, detail=f"主机连接失败: {exc}")


@router.post("/{host_id}/commands", response_model=HostOperationResponse)
def execute_command(
    host_id: int,
    body: HostCommandRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    host = require_host_access(db, current_user, host_id, "execute")
    if body.use_sudo:
        require_admin(current_user)
    try:
        result, duration_ms, fingerprint = run_host_command(
            host, body.command, body.timeout, body.use_sudo
        )
        add_audit_log(
            db,
            host,
            current_user,
            "execute_sudo_command" if body.use_sudo else "execute_command",
            "success" if result.exit_code == 0 else "failed",
            _client_ip(request),
            command=body.command,
            result=result,
            duration_ms=duration_ms,
        )
        return HostOperationResponse(
            success=result.exit_code == 0,
            exit_code=result.exit_code,
            stdout=result.stdout,
            stderr=result.stderr,
            duration_ms=duration_ms,
            fingerprint=fingerprint,
        )
    except Exception as exc:
        db.rollback()
        add_audit_log(
            db,
            host,
            current_user,
            "execute_sudo_command" if body.use_sudo else "execute_command",
            "failed",
            _client_ip(request),
            command=body.command,
            error=str(exc),
        )
        raise HTTPException(status_code=502, detail=f"命令执行失败: {exc}")


@router.get("/{host_id}/docker/containers")
def get_docker_containers(
    host_id: int,
    request: Request,
    paging: PageParams = Depends(),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    host = require_host_access(db, current_user, host_id, "docker")
    if host.host_type != "docker":
        raise HTTPException(status_code=400, detail="该主机未启用 Docker 管理")
    try:
        result, duration_ms, containers = list_docker_containers(host)
        add_audit_log(
            db,
            host,
            current_user,
            "docker_list",
            "success" if result.exit_code == 0 else "failed",
            _client_ip(request),
            result=result,
            duration_ms=duration_ms,
        )
        if result.exit_code != 0:
            raise HTTPException(status_code=502, detail=result.stderr or "Docker 查询失败")
        if paging.search:
            containers = [row for row in containers if paging.search.lower() in (" ".join(row.get("Names", [])) + row.get("Image", "")).lower()]
        containers.sort(key=lambda row: row.get("Id", ""))
        total = len(containers)
        start = ((paging.page or 1) - 1) * paging.page_size
        items = containers[start:start + paging.page_size]
        return {
            "items": items, "total": total, "page": paging.page or 1, "page_size": paging.page_size,
            "success": True,
            "containers": items,
            "duration_ms": duration_ms,
            "fingerprint": None,
        }
    except HTTPException:
        raise
    except Exception as exc:
        db.rollback()
        add_audit_log(
            db, host, current_user, "docker_list", "failed", _client_ip(request), error=str(exc)
        )
        raise HTTPException(status_code=502, detail=f"Docker 查询失败: {exc}")


@router.post("/{host_id}/docker/actions", response_model=HostOperationResponse)
def docker_action(
    host_id: int,
    body: DockerActionRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    host = require_host_access(db, current_user, host_id, "docker")
    if host.host_type != "docker":
        raise HTTPException(status_code=400, detail="该主机未启用 Docker 管理")
    try:
        result, duration_ms = run_docker_action(
            host, body.action, body.container, body.timeout
        )
        add_audit_log(
            db,
            host,
            current_user,
            f"docker_{body.action}",
            "success" if result.exit_code == 0 else "failed",
            _client_ip(request),
            target=body.container,
            result=result,
            duration_ms=duration_ms,
        )
        return HostOperationResponse(
            success=result.exit_code == 0,
            exit_code=result.exit_code,
            stdout=result.stdout,
            stderr=result.stderr,
            duration_ms=duration_ms,
            fingerprint=None,
        )
    except Exception as exc:
        db.rollback()
        add_audit_log(
            db,
            host,
            current_user,
            f"docker_{body.action}",
            "failed",
            _client_ip(request),
            target=body.container,
            error=str(exc),
        )
        raise HTTPException(status_code=502, detail=f"Docker 操作失败: {exc}")


@router.get("/access/subjects", response_model=List[AccessSubjectResponse] | Page[AccessSubjectResponse])
def list_access_subjects(
    paging: PageParams = Depends(),
    subject_type: Optional[str] = Query(None, pattern="^(user|api_key)$"),
    selected: Optional[str] = Query(None, pattern=r"^(user|api_key):[1-9][0-9]*$"),
    active_only: bool = Query(False),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_admin(current_user)
    users = db.query(
        User.id.label("id"), literal("user").label("subject_type"), User.username.label("name"),
        User.is_active.label("is_active"), User.role.label("role"),
        (User.ssh_public_key.isnot(None) & (User.ssh_public_key != "")).label("has_ssh_public_key"),
    )
    keys = db.query(
        ApiKey.id, literal("api_key"), ApiKey.description,
        ApiKey.is_active & (ApiKey.expires_at.is_(None) | (ApiKey.expires_at > datetime.utcnow())),
        literal(None), literal(False),
    )
    subjects = users.union_all(keys).subquery()
    query = db.query(subjects)
    if subject_type:
        query = query.filter(subjects.c.subject_type == subject_type)
    if selected:
        kind, identifier = selected.split(":")
        query = query.filter(subjects.c.subject_type == kind, subjects.c.id == int(identifier))
    if active_only:
        query = query.filter(subjects.c.is_active.is_(True))
    query = search_query(query, paging.search, subjects.c.name)
    def response(row):
        return AccessSubjectResponse(id=row.id, subject_type=row.subject_type, name=row.name,
            description="系统用户" if row.subject_type == "user" else f"API Key #{row.id}",
            is_active=bool(row.is_active), role=row.role, has_ssh_public_key=bool(row.has_ssh_public_key))
    return paginate(query.order_by(subjects.c.name, subjects.c.subject_type, subjects.c.id), paging, response)


@router.post("/access/users", response_model=AccessSubjectResponse, status_code=201)
def create_managed_user(
    body: ManagedUserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_admin(current_user)
    user = User(
        username=body.username,
        password_hash=get_password_hash(body.password),
        role=body.role,
        is_active=True,
        ssh_public_key=body.ssh_public_key,
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="用户名或 SSH 公钥已存在")
    db.refresh(user)
    return AccessSubjectResponse(
        subject_type="user",
        id=user.id,
        name=user.username,
        description="系统用户",
        is_active=user.is_active,
        role=user.role,
        has_ssh_public_key=bool(user.ssh_public_key),
    )


@router.put("/access/users/{user_id}", response_model=AccessSubjectResponse)
def update_managed_user(
    user_id: int,
    body: ManagedUserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_admin(current_user)
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    values = body.model_dump(exclude_unset=True)
    if "role" in values and user.role == "admin" and values["role"] != "admin":
        admin_count = db.query(User).filter(User.role == "admin", User.is_active.is_(True)).count()
        if admin_count <= 1:
            raise HTTPException(status_code=409, detail="必须保留至少一个启用的管理员")
    if values.get("is_active") is False and user.role == "admin":
        admin_count = db.query(User).filter(User.role == "admin", User.is_active.is_(True)).count()
        if admin_count <= 1:
            raise HTTPException(status_code=409, detail="必须保留至少一个启用的管理员")
    if "password" in values:
        user.password_hash = get_password_hash(values.pop("password"))
    for field, value in values.items():
        setattr(user, field, value)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="该 SSH 公钥已绑定其他用户")
    db.refresh(user)
    return AccessSubjectResponse(
        subject_type="user",
        id=user.id,
        name=user.username,
        description="系统用户",
        is_active=user.is_active,
        role=user.role,
        has_ssh_public_key=bool(user.ssh_public_key),
    )


@router.get("/access/grants", response_model=List[HostGrantResponse] | Page[HostGrantResponse])
def list_grants(
    paging: PageParams = Depends(),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_admin(current_user)
    query = db.query(HostAccessGrant).join(ManagedHost).order_by(HostAccessGrant.id.desc())
    query = search_query(query, paging.search, ManagedHost.name)
    return paginate(query, paging, lambda row: _grant_response(db, row))


@router.post("/access/grants", response_model=HostGrantResponse, status_code=201)
def create_grant(
    body: HostGrantCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_admin(current_user)
    host = db.query(ManagedHost).filter(ManagedHost.id == body.host_id).first()
    if not host:
        raise HTTPException(status_code=404, detail="主机不存在")
    validate_subject(db, body.subject_type, body.subject_id)
    grant = HostAccessGrant(
        **body.model_dump(),
        created_by_user_id=current_user.id if current_user.id > 0 else None,
    )
    db.add(grant)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="该主体已获得此主机授权")
    db.refresh(grant)
    return _grant_response(db, grant)


@router.put("/access/grants/{grant_id}", response_model=HostGrantResponse)
def update_grant(
    grant_id: int,
    body: HostGrantUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_admin(current_user)
    grant = db.query(HostAccessGrant).filter(HostAccessGrant.id == grant_id).first()
    if not grant:
        raise HTTPException(status_code=404, detail="授权不存在")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(grant, field, value)
    db.commit()
    db.refresh(grant)
    return _grant_response(db, grant)


@router.delete("/access/grants/{grant_id}", status_code=204)
def delete_grant(
    grant_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_admin(current_user)
    grant = db.query(HostAccessGrant).filter(HostAccessGrant.id == grant_id).first()
    if not grant:
        raise HTTPException(status_code=404, detail="授权不存在")
    db.delete(grant)
    db.commit()


def _audit_query(db, user, host_id=None, search="", action=None, status_filter=None, start_time=None, end_time=None):
    query = db.query(HostAuditLog).options(joinedload(HostAuditLog.host))
    if not is_admin(user):
        actor_type, actor_id, _ = actor_identity(user)
        query = query.filter(HostAuditLog.actor_type == actor_type, HostAuditLog.actor_id == actor_id)
    if host_id:
        query = query.filter(HostAuditLog.host_id == host_id)
    if action:
        query = query.filter(HostAuditLog.action == action)
    if status_filter:
        query = query.filter(HostAuditLog.status == status_filter)
    def utc(value):
        return value.astimezone(timezone.utc).replace(tzinfo=None) if value and value.tzinfo else value
    start_time, end_time = utc(start_time), utc(end_time)
    if start_time and end_time and start_time > end_time:
        raise HTTPException(status_code=422, detail="开始时间不能晚于结束时间")
    if start_time:
        query = query.filter(HostAuditLog.created_at >= start_time)
    if end_time:
        query = query.filter(HostAuditLog.created_at <= end_time)
    if search:
        query = query.join(ManagedHost)
        query = search_query(query, search, ManagedHost.name, HostAuditLog.actor_name, HostAuditLog.client_ip, HostAuditLog.command, HostAuditLog.target)
    return query


def _audit_response(row):
    return HostAuditResponse(
        id=row.id, host_id=row.host_id, host_name=row.host.name if row.host else f"主机 #{row.host_id}",
        actor_type=row.actor_type, actor_id=row.actor_id, actor_name=row.actor_name,
        action=row.action, target=row.target, command=row.command, status=row.status,
        exit_code=row.exit_code, stdout=row.stdout, stderr=row.stderr, client_ip=row.client_ip,
        duration_ms=row.duration_ms, created_at=row.created_at,
        bytes_sent=row.bytes_sent, bytes_received=row.bytes_received,
    )


@router.get("/audit/traffic")
def get_host_traffic(
    host_id: Optional[int] = Query(None, gt=0),
    search: str = Query("", max_length=200),
    action: Optional[str] = Query(None, max_length=50),
    status_filter: Optional[str] = Query(None, alias="status", max_length=20),
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """汇总保留审计记录中的应用层字节；普通用户/API Key 仅统计自己的访问。"""
    query = _audit_query(db, current_user, host_id, search, action, status_filter, start_time, end_time)
    measured = HostAuditLog.bytes_sent.isnot(None) | HostAuditLog.bytes_received.isnot(None)
    row = query.with_entities(
        func.coalesce(func.sum(HostAuditLog.bytes_sent), 0),
        func.coalesce(func.sum(HostAuditLog.bytes_received), 0),
        func.coalesce(func.sum(case((measured, 1), else_=0)), 0),
        func.count(HostAuditLog.id),
    ).one()
    return {"bytes_sent": row[0], "bytes_received": row[1], "measured_count": row[2], "record_count": row[3]}


@router.get("/audit/logs", response_model=List[HostAuditResponse] | Page[HostAuditResponse])
def list_audit_logs(
    paging: PageParams = Depends(),
    host_id: Optional[int] = Query(None, gt=0),
    action: Optional[str] = Query(None, max_length=50),
    status_filter: Optional[str] = Query(None, alias="status", max_length=20),
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = _audit_query(db, current_user, host_id, paging.search, action, status_filter, start_time, end_time)
    if paging.page is None:
        paging.page_size = limit
    return paginate(query.order_by(HostAuditLog.id.desc()), paging, _audit_response)


@router.get("/audit/logs/{log_id}", response_model=HostAuditResponse)
def get_audit_log(log_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    row = _audit_query(db, current_user).filter(HostAuditLog.id == log_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="日志不存在或无权查看")
    return _audit_response(row)


def _delete_audit_query(db, user, query):
    # Keep a fresh maintenance event for every affected host in the same transaction.
    counts = query.with_entities(HostAuditLog.host_id.label("host_id"), func.count(HostAuditLog.id).label("count")).group_by(HostAuditLog.host_id).subquery()
    actor_type, actor_id, actor_name = actor_identity(user)
    db.execute(insert(HostAuditLog).from_select(
        ["host_id", "actor_type", "actor_id", "actor_name", "action", "target", "status", "created_at"],
        select(counts.c.host_id, literal(actor_type), literal(actor_id), literal(actor_name),
               literal("audit_logs_deleted"), literal("删除 ") + cast(counts.c.count, String) + literal(" 条审计记录"),
               literal("success"), literal(datetime.utcnow())),
    ))
    deleted = query.delete(synchronize_session=False)
    db.commit()
    return deleted


@router.post("/audit/delete")
def delete_audit_logs(body: HostAuditDeleteRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    require_admin(current_user)
    query = db.query(HostAuditLog).filter(HostAuditLog.id.in_(body.ids))
    return {"deleted": _delete_audit_query(db, current_user, query)}


@router.post("/audit/cleanup")
def cleanup_audit_logs(body: HostAuditCleanupRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    require_admin(current_user)
    cutoff = datetime.utcnow() - timedelta(days=body.keep_days)
    query = db.query(HostAuditLog).filter(HostAuditLog.created_at < cutoff)
    if body.host_id:
        query = query.filter(HostAuditLog.host_id == body.host_id)
    count = query.count()
    if body.dry_run:
        return {"count": count, "before": cutoff, "deleted": 0}
    deleted = _delete_audit_query(db, current_user, query)
    return {"count": count, "before": cutoff, "deleted": deleted}
