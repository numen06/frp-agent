"""Persist bounded samples and probe registered SSH proxies without credentials."""
import logging
import re
import socket
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from pathlib import Path

from app.database import SessionLocal
from app.config import get_settings
from app.frps_client import FrpsCollectionError
from app.models.frps_server import FrpsServer
from app.models.proxy import Proxy
from app.models.runtime import ProxyProbe, RuntimeSample, ServerSyncState
from app.services.runtime_service import resource_sampler, read
from app.services.builtin_frps_config import parse_document

logger = logging.getLogger(__name__)
SAMPLE_SECONDS = 60
PROBE_SECONDS = 300
RETENTION_DAYS = 7


async def collect_proxy_snapshot(db, server, client):
    started, attempted = time.monotonic(), datetime.utcnow()
    try:
        snapshot = await client.get_all_proxies()
    except FrpsCollectionError as exc:
        db.rollback()
        state = db.get(ServerSyncState, server.id) or ServerSyncState(server_id=server.id)
        state.attempted_at, state.status, state.message = attempted, 'failed', str(exc)
        state.duration_ms = round((time.monotonic() - started) * 1000)
        db.add(state)
        db.commit()
        raise
    state = db.get(ServerSyncState, server.id) or ServerSyncState(server_id=server.id)
    state.attempted_at, state.succeeded_at = attempted, datetime.utcnow()
    state.status, state.message = 'success', '状态采集成功'
    state.duration_ms = round((time.monotonic() - started) * 1000)
    db.add(state)
    return snapshot


def sample_runtime():
    from app.services.rdp_gateway_service import rdp_gateway_service
    try:
        metrics = resource_sampler.sample()
        metrics['rdp'] = rdp_gateway_service.metrics(flush=True)
        with SessionLocal() as db:
            db.add(RuntimeSample(metrics=metrics))
            db.query(RuntimeSample).filter(RuntimeSample.collected_at < datetime.utcnow() - timedelta(days=RETENTION_DAYS)).delete()
            db.commit()
    except Exception:
        logger.exception('资源采集失败')


def probe_ssh(address, port, timeout=3):
    """A TCP accept is insufficient: require an actual SSH identification line."""
    started = time.monotonic()
    status, message = 'failed', '未收到有效 SSH 握手'
    try:
        with socket.create_connection((address, port), timeout=timeout) as sock:
            data = b''
            while len(data) < 4096:
                remaining = timeout - (time.monotonic() - started)
                if remaining <= 0:
                    raise TimeoutError()
                sock.settimeout(remaining)
                chunk = sock.recv(min(512, 4096 - len(data)))
                if not chunk:
                    message = '连接被目标关闭，未收到 SSH 握手'
                    break
                data += chunk
                if any(re.fullmatch(rb'SSH-(?:2\.0|1\.99)-[^\r\n]+\r?', line) for line in data.split(b'\n')[:-1]):
                    status, message = 'healthy', 'SSH 握手正常（未验证登录）'
                    break
    except OSError as exc:
        message = 'SSH 握手超时' if isinstance(exc, TimeoutError) else '连接失败（' + type(exc).__name__ + '）'
    return dict(status=status, message=message, duration_ms=round((time.monotonic() - started) * 1000))


def probe_address(server):
    if not server.is_builtin:
        return server.server_addr
    # The local instance may not be able to hairpin through its own public NAT.
    document = parse_document(read(Path(get_settings().builtin_frps_dir) / 'frps.toml'))
    address = document.get('proxyBindAddr') or document.get('bindAddr') or '0.0.0.0'
    return {'0.0.0.0': '127.0.0.1', '::': '::1'}.get(address, address)


def probe_connections():
    try:
        with SessionLocal() as db:
            targets = {s.id: probe_address(s) for s in db.query(FrpsServer).filter(FrpsServer.is_active.is_(True))}
            candidates = [(p.id, s.server_addr, p.remote_port, targets[s.id]) for p, s in db.query(Proxy, FrpsServer).join(
                FrpsServer, Proxy.frps_server_id == FrpsServer.id).filter(
                FrpsServer.is_active.is_(True), Proxy.status == 'online', Proxy.proxy_type == 'tcp',
                Proxy.remote_port.isnot(None)).all()
                if p.local_port == 22 or re.search(r'(?:^|[_.-])ssh\d*$', p.name, re.I)]
        # Four short probes at a time; no credentials, package installs, or remote commands.
        with ThreadPoolExecutor(max_workers=4) as pool:
            results = list(pool.map(lambda item: (item, probe_ssh(item[3], item[2]), datetime.utcnow()), candidates))
        with SessionLocal() as db:
            for (proxy_id, address, port, target), result, checked_at in results:
                proxy = db.get(Proxy, proxy_id)
                if not proxy or proxy.status != 'online' or proxy.remote_port != port:
                    continue
                server = db.get(FrpsServer, proxy.frps_server_id)
                if not server or not server.is_active or server.server_addr != address:
                    continue
                row = db.get(ProxyProbe, proxy_id) or ProxyProbe(proxy_id=proxy_id)
                if target != address:
                    result['message'] += '；经本机监听地址检查'
                row.checked_at, row.address, row.port = checked_at, address, port
                for key, value in result.items():
                    setattr(row, key, value)
                db.add(row)
            db.query(ProxyProbe).filter(~ProxyProbe.proxy_id.in_(db.query(Proxy.id))).delete(synchronize_session=False)
            db.commit()
    except Exception:
        logger.exception('SSH 代理握手检查失败')
