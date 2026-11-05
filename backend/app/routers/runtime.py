"""Administrator-only runtime overview; all timestamps explicitly use UTC."""
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.config import get_settings
from app.database import get_db
from app.models.frps_server import FrpsServer
from app.models.history import ProxyHistory
from app.models.proxy import Proxy
from app.models.runtime import ProxyProbe, RuntimeSample, ServerSyncState
from app.models.user import User
from app.services.host_access_service import require_admin
from app.services.monitoring_service import SAMPLE_SECONDS, PROBE_SECONDS, RETENTION_DAYS

router = APIRouter(prefix='/api/system', tags=['运行监控'])


def utc(value):
    return value.isoformat() + 'Z' if value else None


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
                history=list(buckets.values()), events=events)
