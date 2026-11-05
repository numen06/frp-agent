"""Admin-only proxy discovery. No credentials are tried and no grants are created."""
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from app.auth import get_current_user
from app.database import get_db
from app.models.user import User
from app.models.managed_host import ManagedHost, HostProxySource
from app.services.host_access_service import require_admin, add_audit_log
from app.services.host_discovery import discover, scan_lock

router = APIRouter(prefix="/api/managed-hosts", tags=["代理导入"])


class ImportHosts(BaseModel):
    proxy_ids: list[int] = Field(min_length=1, max_length=100)


def scan(db, ids=None):
    if not scan_lock.acquire(blocking=False):
        raise HTTPException(409, "已有代理导入任务正在运行，请稍后重试")
    try:
        return discover(db, ids)
    finally:
        scan_lock.release()


@router.post("/discovery/scan")
def scan_hosts(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    require_admin(user)
    return {"items": scan(db)}


@router.post("/discovery/import")
def import_hosts(body: ImportHosts, request: Request, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    require_admin(user)
    if not scan_lock.acquire(blocking=False):
        raise HTTPException(409, "已有识别或导入任务正在运行，请稍后重试")
    try:
        ids = set(body.proxy_ids)
        rows = discover(db, ids)
        if {r["proxy_id"] for r in rows} != ids:
            raise HTTPException(400, "包含不存在或不支持的代理，请重新检测")
        failed = [r for r in rows if not r["available"] and not r["existing_host_id"]]
        if failed:
            raise HTTPException(409, f"代理“{failed[0]['name']}”当前不可用：{failed[0]['message']}；未创建任何主机，请重新检测")
        created, existing = [], []
        for row in rows:
            if row["existing_host_id"]:
                existing.append(row["existing_host_id"])
                continue
            name = row["name"][:100]
            if db.query(ManagedHost.id).filter(ManagedHost.name == name).first():
                suffix = f"-proxy-{row['proxy_id']}"
                name = name[:100-len(suffix)] + suffix
            host = ManagedHost(name=name, address=row["address"], port=row["port"], host_type=row["host_type"],
                docker_use_tls=row["docker_use_tls"], docker_verify_tls=True, is_active=False, last_status="unknown",
                last_message="代理导入，未激活；请配置凭据并通过连接测试", description=f"从 {row['server_name']} / {row['name']} 识别",
                created_by_user_id=user.id if user.id > 0 else None)
            db.add(host)
            try:
                db.flush()
                db.add(HostProxySource(host_id=host.id, proxy_id=row["proxy_id"], activation_pending=True))
                db.flush()
            except IntegrityError:
                db.rollback()
                raise HTTPException(409, "主机或代理已被其他操作加入，请重新检测；本批次未创建主机")
            created.append(host.id)
        db.commit()
        for hid in created:
            add_audit_log(db, db.get(ManagedHost, hid), user, "discovery_import", "success", request.client.host if request.client else None)
        return {"created_ids": created, "existing_ids": existing}
    finally:
        scan_lock.release()



@router.get("/ssh-protection")
def ssh_protection(user: User = Depends(get_current_user)):
    require_admin(user)
    import json
    import time
    from pathlib import Path
    from app.config import get_settings
    from app.services.ssh_gateway_service import (MAX_AUTH_FAILURES, AUTH_FAILURE_WINDOW_SECONDS,
        AUTH_FAILURE_BAN_THRESHOLD, AUTH_BAN_SECONDS, MAX_GATEWAY_SESSIONS, MAX_GATEWAY_SESSIONS_PER_IP,
        HANDSHAKE_TIMEOUT_SECONDS, AUTH_DEADLINE_SECONDS)
    from app.routers.webssh import _sessions, MAX_SESSIONS, MAX_PER_USER, MAX_AGE, IDLE_TIMEOUT
    key_path = Path(get_settings().ssh_gateway_host_key_path)
    if not key_path.is_absolute():
        key_path = Path(__file__).resolve().parents[3] / key_path
    path = key_path.parent / "ssh_gateway_bans.json"
    bans = []
    try:
        if path.exists():
            if path.stat().st_size > 1_000_000:
                raise ValueError()
            data = json.loads(path.read_text(encoding="utf-8"))
            if data.get("version") != 1 or not isinstance(data.get("bans"), dict):
                raise ValueError()
            import ipaddress
            for ip, until in data["bans"].items():
                ipaddress.ip_address(ip)
                if float(until) > time.time():
                    bans.append({"ip": ip, "until": float(until)})
    except (OSError, ValueError, TypeError, AttributeError):
        raise HTTPException(503, "SSH 网关封禁记录读取失败，请检查运行日志；不能将读取失败视为没有封禁")
    metrics_path = path.parent / "ssh_gateway_metrics.json"
    native_metrics, metrics_error = None, ""
    try:
        if not metrics_path.exists():
            metrics_error = "正在等待 SSH 网关日志首次采集"
        else:
            if metrics_path.stat().st_size > 100_000:
                raise ValueError()
            metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
            if metrics.get("version") != 1 or not isinstance(metrics.get("counts"), dict) or any(
                    not isinstance(v, int) or v < 0 for v in metrics["counts"].values()):
                raise ValueError()
            native_metrics = {key: metrics.get(key) for key in ["counts", "collected_at", "first_log_at", "started_at"]}
            if time.time() - float(metrics["collected_at"]) > 120:
                metrics_error = "SSH 网关日志采集已过期，请检查采集服务；下方保留上次结果"
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        metrics_error = "SSH 网关日志统计读取失败，请检查采集服务；不能将读取失败视为零次"
        native_metrics = None
    return {"native_metrics": native_metrics, "metrics_error": metrics_error, "collected_at": time.time(), "bans": bans,
        "policy": {"max_auth_attempts": MAX_AUTH_FAILURES, "window_seconds": AUTH_FAILURE_WINDOW_SECONDS,
            "ban_threshold": AUTH_FAILURE_BAN_THRESHOLD, "ban_seconds": AUTH_BAN_SECONDS,
            "max_sessions": MAX_GATEWAY_SESSIONS, "max_sessions_per_ip": MAX_GATEWAY_SESSIONS_PER_IP,
            "handshake_timeout": HANDSHAKE_TIMEOUT_SECONDS, "auth_timeout": AUTH_DEADLINE_SECONDS},
        "webssh": {"active": sum(_sessions.values()), "max_sessions": MAX_SESSIONS, "max_per_user": MAX_PER_USER,
            "max_age": MAX_AGE, "idle_timeout": IDLE_TIMEOUT}}
