"""Administrator-only runtime overview; all timestamps explicitly use UTC."""
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, Response
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.auth import get_current_user
from app.config import get_settings
from app.database import get_db
from app.models.frps_server import FrpsServer
from app.models.history import ProxyHistory
from app.models.proxy import Proxy
from app.models.runtime import ProxyProbe, RuntimeSample, ServerSyncState
from app.models.user import User
from app.models.managed_host import HostAuditLog, ManagedHost
from app.services.host_access_service import require_admin
from app.services.monitoring_service import SAMPLE_SECONDS, PROBE_SECONDS, RETENTION_DAYS

router = APIRouter(prefix='/api/system', tags=['运行监控'])


def utc(value):
    return value.isoformat() + 'Z' if value else None


def vnc_overview(db, now):
    """Shared audit data works across the HTTP and WebSocket worker processes."""
    hosts = db.query(ManagedHost).options(joinedload(ManagedHost.credential)).filter_by(host_type='vnc').order_by(ManagedHost.name).all()
    ssh_ids = {host.vnc_ssh_host_id for host in hosts if host.vnc_ssh_host_id}
    ssh_hosts = {host.id: host for host in db.query(ManagedHost).options(joinedload(ManagedHost.credential)).filter(ManagedHost.id.in_(ssh_ids)).all()}
    rows = []
    for host in hosts:
        ssh = ssh_hosts.get(host.vnc_ssh_host_id)
        issues = []
        if host.address != '127.0.0.1':
            issues.append('目标必须为 Mac 回环地址')
        if not host.credential or host.credential.auth_type != 'password' or not host.credential.password_encrypted:
            issues.append('缺少 VNC 密码凭据')
        if not ssh or ssh.host_type != 'ssh':
            issues.append('关联的 SSH 主机不可用')
        else:
            if not ssh.is_active:
                issues.append('关联的 SSH 主机已停用')
            if not ssh.credential or not (
                    ssh.credential.auth_type == 'password' and ssh.credential.password_encrypted or
                    ssh.credential.auth_type == 'private_key' and ssh.credential.private_key_encrypted):
                issues.append('SSH 主机缺少凭据')
            if not ssh.host_key_fingerprint:
                issues.append('SSH 指纹尚未固定')
        # A previous successful manual check is not a continuous health probe.
        rows.append(dict(id=host.id, name=host.name, enabled=host.is_active,
                         ssh_name=ssh.name if ssh else None, issues=issues,
                         checked_at=utc(host.last_checked_at),
                         check_status=host.last_status if host.last_checked_at else 'unknown'))
    audit = db.query(HostAuditLog).filter(HostAuditLog.created_at >= now - timedelta(hours=24),
                                        HostAuditLog.action.in_(['vnc_connected', 'vnc_session']))
    connected = ended = failed = sent = received = 0
    for action, status, count, upload, download in audit.with_entities(
            HostAuditLog.action, HostAuditLog.status, func.count(HostAuditLog.id),
            func.sum(HostAuditLog.bytes_sent), func.sum(HostAuditLog.bytes_received)).group_by(
                HostAuditLog.action, HostAuditLog.status).all():
        if action == 'vnc_connected' and status == 'success':
            connected += count
        if action == 'vnc_session':
            ended += count
            failed += count if status == 'failed' else 0
            sent += upload or 0
            received += download or 0
    failures = [dict(host_id=log.host_id, name=name, at=utc(log.created_at))
                for log, name in audit.join(ManagedHost, ManagedHost.id == HostAuditLog.host_id).with_entities(
                    HostAuditLog, ManagedHost.name).filter(HostAuditLog.action == 'vnc_session', HostAuditLog.status == 'failed').order_by(
                    HostAuditLog.created_at.desc(), HostAuditLog.id.desc()).limit(8)]
    return dict(collected_at=utc(now), total=len(rows), enabled=sum(row['enabled'] for row in rows),
                needs_attention=sum(row['enabled'] and bool(row['issues']) for row in rows),
                connected=connected, ended=ended, failed=failed, bytes_sent=sent, bytes_received=received,
                hosts=rows[:100], truncated=len(rows) > 100, failures=failures)


@router.get('/overview')
def overview(response: Response, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    require_admin(current_user)
    response.headers['Cache-Control'] = 'no-store'
    now = datetime.utcnow()
    latest = db.query(RuntimeSample).order_by(RuntimeSample.collected_at.desc(), RuntimeSample.id.desc()).first()
    interval = get_settings().sync_interval_seconds
    servers = []
    for server, state in db.query(FrpsServer, ServerSyncState).outerjoin(
            ServerSyncState, ServerSyncState.server_id == FrpsServer.id).filter(FrpsServer.is_active.is_(True)).all():
        stale = not state or not state.succeeded_at or (now - state.succeeded_at).total_seconds() > max(180, interval * 3)
        servers.append(dict(id=server.id, name=server.name,
                            status='unknown' if not state else 'failed' if state.status == 'failed' else 'stale' if stale else 'success',
                            attempted_at=utc(state.attempted_at) if state else None,
                            succeeded_at=utc(state.succeeded_at) if state else None,
                            message=state.message if state else '尚未采集', duration_ms=state.duration_ms if state else None))
    valid_servers = {s['id'] for s in servers if s['status'] == 'success'}
    probes = []
    for probe, proxy, server in db.query(ProxyProbe, Proxy, FrpsServer).join(
            Proxy, Proxy.id == ProxyProbe.proxy_id).join(FrpsServer, FrpsServer.id == Proxy.frps_server_id).filter(
            Proxy.status == 'online', FrpsServer.is_active.is_(True)).all():
        if probe.address != server.server_addr or probe.port != proxy.remote_port:
            continue
        stale = (now - probe.checked_at).total_seconds() > PROBE_SECONDS * 2 or server.id not in valid_servers
        probes.append(dict(name=proxy.name, server=server.name, checked_at=utc(probe.checked_at),
                           status='stale' if stale else probe.status, message=probe.message, duration_ms=probe.duration_ms))
    buckets = {}
    for stamp, metrics in db.query(RuntimeSample.collected_at, RuntimeSample.metrics).filter(
            RuntimeSample.collected_at >= now - timedelta(hours=24)).order_by(RuntimeSample.collected_at).all():
        bucket = stamp.replace(minute=stamp.minute // 30 * 30, second=0, microsecond=0)
        point = buckets.setdefault(bucket, dict(at=utc(bucket), cpu_percent=None, memory_percent=None, host_memory_percent=None, samples=0))
        point['samples'] += 1
        for key, value in [('cpu_percent', metrics['app']['cpu_percent']), ('memory_percent', metrics['app']['memory_percent']),
                           ('host_memory_percent', metrics['host']['memory_percent'])]:
            if value is not None:
                point[key] = max(point[key], value) if point[key] is not None else value
    events = [dict(server_id=e.frps_server_id, name=e.proxy_name, action=e.action, at=utc(e.timestamp))
              for e in db.query(ProxyHistory).filter(ProxyHistory.action.in_(['online', 'offline', 'discovered']),
                    ProxyHistory.timestamp >= now - timedelta(days=RETENTION_DAYS)).order_by(
                    ProxyHistory.timestamp.desc(), ProxyHistory.id.desc()).limit(12)]
    return dict(now=utc(now), sample_interval_seconds=SAMPLE_SECONDS, probe_interval_seconds=PROBE_SECONDS,
                sync_interval_seconds=interval, retention_days=RETENTION_DAYS,
                latest=latest.metrics if latest else None,
                sample_stale=not latest or (now - latest.collected_at).total_seconds() > SAMPLE_SECONDS * 3,
                servers=servers, probes=sorted(probes, key=lambda p: (p['status'] == 'healthy', p['name'])),
                history=list(buckets.values()), events=events, vnc=vnc_overview(db, now))
