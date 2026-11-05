"""Operational data must distinguish unknown, stale, offline, and probe failure."""
import asyncio
import io
from datetime import datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.auth import get_current_user
from app.database import Base, get_db
from app.frps_client import FrpsClient, FrpsCollectionError, PROXY_TYPES
from app.main import app
from app.models.frps_server import FrpsServer
from app.models.proxy import Proxy
from app.models.history import ProxyHistory
from app.models.runtime import RuntimeSample, ServerSyncState, ProxyProbe
from app.models.user import User
from app.models.managed_host import ManagedHost, HostAuditLog
from app.models.ssh_credential import SshCredential
from app.services import monitoring_service, runtime_service
from app.services.rdp_gateway_service import RDPGatewayService


@pytest.fixture
def db():
    engine = create_engine('sqlite://', connect_args={'check_same_thread': False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    engine.dispose()


def server_and_proxy(db):
    server = FrpsServer(name='node', server_addr='example.test', api_base_url='http://example.test/api', auth_username='test', auth_password='not-logged')
    db.add(server); db.flush()
    proxy = Proxy(frps_server_id=server.id, name='nas_ssh', proxy_type='tcp', remote_port=6020, local_port=22, status='online')
    db.add(proxy); db.commit()
    return server, proxy


@pytest.mark.parametrize('response', [httpx.Response(503), httpx.Response(200, json={}), httpx.Response(200, json={'proxies': [{}]})])
def test_partial_collection_is_never_a_successful_empty_snapshot(monkeypatch, response):
    original = httpx.AsyncClient
    seen = []
    def handle(request):
        kind = request.url.path.rsplit('/', 1)[-1]; seen.append(kind)
        return response if kind == 'tcp' else httpx.Response(200, json={'proxies': None})
    monkeypatch.setattr(httpx, 'AsyncClient', lambda **kw: original(transport=httpx.MockTransport(handle), **kw))
    client = FrpsClient(SimpleNamespace(api_base_url='http://example.test/api', auth_username='u', auth_password='secret'))
    with pytest.raises(FrpsCollectionError) as error:
        asyncio.run(client.get_all_proxies())
    assert 'secret' not in str(error.value) and set(seen) == set(PROXY_TYPES)


def test_optional_404_is_not_a_successful_empty_type(monkeypatch):
    original = httpx.AsyncClient
    def handle(request):
        kind = request.url.path.rsplit('/', 1)[-1]
        return httpx.Response(404) if kind == 'sudp' else httpx.Response(200, json={'proxies': None})
    monkeypatch.setattr(httpx, 'AsyncClient', lambda **kw: original(transport=httpx.MockTransport(handle), **kw))
    client = FrpsClient(SimpleNamespace(api_base_url='http://example.test/api', auth_username='u', auth_password='p'))
    snapshot = asyncio.run(client.get_all_proxies())
    assert 'sudp' not in snapshot and snapshot['stcp'] == []


@pytest.mark.parametrize('flow', ['scheduler', 'compare', 'list'])
@pytest.mark.parametrize('failure', [True, False])
def test_every_sync_path_preserves_failure_and_records_real_offline(db, monkeypatch, flow, failure):
    server, proxy = server_and_proxy(db)
    async def snapshot(self):
        if failure:
            raise FrpsCollectionError('TCP 状态采集失败，保留上次状态')
        return {'tcp': [dict(name='nas_ssh', status='offline', conf={'remotePort': 6020})]}
    async def version(self): return '0.71.1'
    monkeypatch.setattr(FrpsClient, 'get_all_proxies', snapshot)
    monkeypatch.setattr(FrpsClient, 'get_server_version', version)
    async def run():
        if flow == 'scheduler':
            from app.scheduler import sync_server
            return await sync_server(db, server)
        if flow == 'compare':
            from app.routers.sync import compare_proxies
            return await compare_proxies(server.id, True, db, User(id=1, role='admin'))
        from app.routers.proxy import get_proxies
        return await get_proxies(server.id, None, None, None, 1, 20, True, db, User(id=1, role='admin'))
    if failure and flow != 'list':
        with pytest.raises(FrpsCollectionError): asyncio.run(run())
    else:
        result = asyncio.run(run())
        if failure: assert result['analysis']['error']
    db.expire_all()
    assert db.get(Proxy, proxy.id).status == ('online' if failure else 'offline')
    assert db.query(ProxyHistory).filter_by(action='offline').count() == (0 if failure else 1)
    assert db.get(ServerSyncState, server.id).status == ('failed' if failure else 'success')
    if not failure:
        asyncio.run(run())
        assert db.query(ProxyHistory).filter_by(action='offline').count() == 1


def test_unsupported_type_is_not_marked_offline(db, monkeypatch):
    server, proxy = server_and_proxy(db); proxy.proxy_type = 'stcp'; db.commit()
    async def snapshot(self): return {'tcp': []}
    async def version(self): return None
    monkeypatch.setattr(FrpsClient, 'get_all_proxies', snapshot)
    monkeypatch.setattr(FrpsClient, 'get_server_version', version)
    from app.scheduler import sync_server
    asyncio.run(sync_server(db, server))
    assert proxy.status == 'online' and db.query(ProxyHistory).count() == 0


def test_resources_use_correct_container_denominator_and_cache(monkeypatch, tmp_path):
    cg = tmp_path / 'cgroup'; cg.mkdir()
    for name, value in {'cpu.stat': 'usage_usec 1000000', 'cpu.max': '50000 100000',
                        'memory.current': '83886080', 'memory.max': '134217728',
                        'memory.stat': 'inactive_file 16777216'}.items():
        (cg / name).write_text(value)
    monkeypatch.setattr(runtime_service, 'cgroup_paths', lambda: {'v2': cg})
    values = runtime_service.container_counters()
    assert values['cpu_quota'] == .5 and values['cpu_seconds'] == 1
    assert values['memory_used_bytes'] == 64 * 1024**2 and values['memory_limit_bytes'] == 128 * 1024**2
    (cg / 'memory.max').write_text('max')
    assert runtime_service.container_counters()['memory_limit_bytes'] is None
    (cg / 'memory.current').unlink()
    assert runtime_service.container_counters()['memory_used_bytes'] is None


def test_v1_mount_root_resolves_to_container_directory(monkeypatch, tmp_path):
    proc = tmp_path / 'proc'; (proc / 'self').mkdir(parents=True)
    (proc / 'self/cgroup').write_text('5:memory:/docker/abc\n4:cpu,cpuacct:/docker/abc')
    (proc / 'self/mountinfo').write_text('11 1 0:1 /docker/abc /sys/fs/cgroup/memory rw - cgroup cgroup rw,memory\n12 1 0:2 /docker/abc /sys/fs/cgroup/cpu rw - cgroup cgroup rw,cpu,cpuacct')
    monkeypatch.setattr(runtime_service, 'PROC', proc)
    assert runtime_service.cgroup_paths() == {'memory': Path('/sys/fs/cgroup/memory'), 'cpu': Path('/sys/fs/cgroup/cpu'), 'cpuacct': Path('/sys/fs/cgroup/cpu')}


def test_cpu_is_normalized_to_quota_not_host_cores(monkeypatch):
    now, used = [100.], [1.]
    monkeypatch.setattr(runtime_service.time, 'monotonic', lambda: now[0])
    monkeypatch.setattr(runtime_service, 'STARTED', 0)
    monkeypatch.setattr(runtime_service.Path, 'exists', lambda self: self.name == '.dockerenv')
    monkeypatch.setattr(runtime_service.os, 'cpu_count', lambda: 4)
    monkeypatch.setattr(runtime_service.os, 'sched_getaffinity', lambda _: {0, 1, 2, 3}, raising=False)
    monkeypatch.setattr(runtime_service, 'container_counters', lambda: dict(cpu_seconds=used[0], cpu_quota=.5,
                       memory_used_bytes=64*1024**2, memory_limit_bytes=128*1024**2))
    def read(path):
        return {'stat': 'cpu 100 0 0 100 0 0 0 0' if now[0] == 100 else 'cpu 120 0 0 180 0 0 0 0',
                'meminfo': 'MemTotal: 1048576 kB\nMemAvailable: 524288 kB', 'uptime': '1000 2000'}.get(Path(path).name, '')
    monkeypatch.setattr(runtime_service, 'read', read)
    sampler = runtime_service.ResourceSampler()
    assert sampler.sample()['app']['cpu_percent'] is None
    now[0], used[0] = 102., 1.25
    sample = sampler.sample()
    assert sample['app']['cpu_percent'] == 25.0 and sample['app']['memory_percent'] == 50.0
    assert sample['host']['cpu_percent'] == 20.0 and sample['host']['memory_percent'] == 50.0


def test_ssh_accept_requires_a_real_fragmented_identification(monkeypatch):
    class Sock:
        def __init__(self, chunks): self.chunks = iter(chunks)
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def settimeout(self, value): pass
        def recv(self, size): return next(self.chunks, b'')
    for chunks, expected in [([b''], 'failed'), ([b'HTTP/1.1 200 OK\r\n'], 'failed'),
                             ([b'notice\r\nSSH-2.', b'0-OpenSSH_9.0\r\n'], 'healthy')]:
        monkeypatch.setattr(monitoring_service.socket, 'create_connection', lambda *a, **kw: Sock(chunks))
        assert monitoring_service.probe_ssh('example.test', 6020)['status'] == expected


def test_rdp_handshake_bans_are_bounded_and_do_not_interrupt_sessions(monkeypatch):
    service = RDPGatewayService(); now = [1000.]
    monkeypatch.setattr('app.services.rdp_gateway_service.time.monotonic', lambda: now[0])
    assert service._admit('198.51.100.10')
    for _ in range(10): service._record_failure('198.51.100.10', 'handshake_failures')
    assert not service._admit('198.51.100.10')
    assert service._active == 1  # Existing connection is not closed.
    assert service._admit('198.51.100.11')
    assert service.metrics()['counts']['handshake_failures'] == 10
    now[0] += 1801
    assert service._admit('198.51.100.10')
    stream = io.StringIO('[ERROR][com.freerdp.core] anything\n[INFO] benign\n')
    service._drain_native_logs(stream)
    assert service.metrics()['counts']['native_error_lines'] == 1 and stream.closed


def test_runtime_overview_is_admin_only_and_marks_stale_data(db):
    server, proxy = server_and_proxy(db)
    stamp = datetime.utcnow() - timedelta(hours=1)
    metrics = dict(app=dict(cpu_percent=None, memory_percent=50), host=dict(memory_percent=60))
    db.add(RuntimeSample(collected_at=stamp, metrics=metrics))
    db.add(ServerSyncState(server_id=server.id, attempted_at=stamp, succeeded_at=stamp, status='failed', message='采集失败'))
    db.add(ProxyProbe(proxy_id=proxy.id, checked_at=stamp, address=server.server_addr, port=6020, status='healthy', message='SSH 握手正常', duration_ms=20))
    db.commit()
    user = [User(id=2, role='user')]
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: user[0]
    try:
        client = TestClient(app)
        assert client.get('/api/system/overview').status_code == 403
        user[0] = User(id=-1, role='admin')
        assert client.get('/api/system/overview').status_code == 403
        user[0] = User(id=1, role='admin')
        response = client.get('/api/system/overview'); result = response.json()
        assert response.status_code == 200 and response.headers['cache-control'] == 'no-store'
        assert result['sample_stale'] and result['servers'][0]['status'] == 'failed'
        assert result['probes'][0]['status'] == 'stale'
        assert result['history'][0]['cpu_percent'] is None
        assert 'not-logged' not in response.text
        assert result['vnc']['total'] == 0 and result['vnc']['connected'] == 0
    finally:
        app.dependency_overrides.clear()


def test_vnc_overview_uses_shared_audit_without_double_counting_or_secrets(db):
    from app.routers.runtime import overview
    from fastapi import Response
    now = datetime.utcnow()
    credential = SshCredential(name='private', username='private-user', auth_type='password', password_encrypted='secret-ciphertext')
    db.add(credential); db.flush()
    ssh = ManagedHost(name='Mac SSH', address='mac.internal', host_type='ssh', credential_id=credential.id, host_key_fingerprint='SHA256:pin')
    db.add(ssh); db.flush()
    host = ManagedHost(name='Mac VNC', address='127.0.0.1', host_type='vnc', credential_id=credential.id, vnc_ssh_host_id=ssh.id,
                       last_status='online', last_checked_at=now-timedelta(days=2))
    broken = ManagedHost(name='Broken VNC', address='127.0.0.1', host_type='vnc')
    disabled = ManagedHost(name='Disabled VNC', address='127.0.0.1', host_type='vnc', is_active=False)
    db.add_all([host, broken, disabled]); db.flush()
    def log(action, status, sent, received, at=now):
        return HostAuditLog(host_id=host.id, actor_type='user', actor_id=1, actor_name='private-user', action=action,
                            status=status, bytes_sent=sent, bytes_received=received, stderr='secret-error', created_at=at)
    db.add_all([log('vnc_connected', 'success', 100, 200), log('vnc_session', 'success', 100, 200),
                log('vnc_session', 'failed', 10, 20), log('ssh_session', 'success', 999, 999),
                log('vnc_connected', 'success', 999, 999, now-timedelta(days=2))]); db.commit()
    result = overview(Response(), db, User(id=1, role='admin'))['vnc']
    assert (result['total'], result['enabled'], result['needs_attention']) == (3, 2, 1)
    assert (result['connected'], result['ended'], result['failed']) == (1, 2, 1)
    assert (result['bytes_sent'], result['bytes_received']) == (110, 220)
    row = next(row for row in result['hosts'] if row['id'] == host.id)
    assert row['issues'] == [] and row['check_status'] == 'online' and row['checked_at'].endswith('Z')
    assert len(result['failures']) == 1 and result['failures'][0]['host_id'] == host.id
    assert not any(secret in str(result) for secret in ['secret-ciphertext', 'secret-error', 'private-user', 'mac.internal', 'SHA256:pin'])
    ssh.is_active = False; ssh.host_key_fingerprint = None; db.commit()
    result = overview(Response(), db, User(id=1, role='admin'))['vnc']
    row = next(row for row in result['hosts'] if row['id'] == host.id)
    assert result['needs_attention'] == 2 and 'SSH 指纹尚未固定' in row['issues']


def test_rdp_upstream_outage_does_not_ban_clients(monkeypatch):
    from unittest.mock import Mock
    service = RDPGatewayService()
    def unavailable(*args, **kwargs): raise ConnectionRefusedError()
    monkeypatch.setattr('app.services.rdp_gateway_service.socket.create_connection', unavailable)
    for _ in range(10):
        assert service._admit('198.51.100.10')
        service._relay(Mock(), '198.51.100.10', 50000)
    metrics = service.metrics()
    assert metrics['blocked_sources'] == 0 and metrics['active'] == 0
    assert metrics['counts']['upstream_errors'] == 10
    assert metrics['counts'].get('handshake_failures', 0) == 0


def test_resource_retention_removes_only_expired_samples(db, monkeypatch):
    from sqlalchemy.orm import sessionmaker
    from app.services.rdp_gateway_service import rdp_gateway_service
    now = datetime.utcnow()
    metrics = dict(app=dict(cpu_percent=None, memory_percent=None), host=dict(memory_percent=None))
    db.add_all([RuntimeSample(collected_at=now-timedelta(days=8), metrics=metrics),
                RuntimeSample(collected_at=now-timedelta(days=1), metrics=metrics)])
    db.commit()
    monkeypatch.setattr(monitoring_service, 'SessionLocal', sessionmaker(bind=db.bind))
    monkeypatch.setattr(monitoring_service.resource_sampler, 'sample', lambda: dict(metrics))
    monkeypatch.setattr(rdp_gateway_service, 'metrics', lambda **kw: dict(counts={}))
    monitoring_service.sample_runtime()
    db.expire_all()
    assert db.query(RuntimeSample).count() == 2
    assert db.query(RuntimeSample).filter(RuntimeSample.collected_at < now-timedelta(days=7)).count() == 0


def test_builtin_probe_uses_actual_listener_without_public_nat(monkeypatch, tmp_path):
    monkeypatch.setattr(monitoring_service.get_settings(), 'builtin_frps_dir', str(tmp_path))
    server = SimpleNamespace(is_builtin=True, server_addr='public.example.test')
    assert monitoring_service.probe_address(server) == '127.0.0.1'
    for text, expected in [('bindAddr="0.0.0.0"', '127.0.0.1'), ('bindAddr="::"', '::1'),
                           ('bindAddr="0.0.0.0"\nproxyBindAddr="192.0.2.10"', '192.0.2.10')]:
        (tmp_path/'frps.toml').write_text(text)
        assert monitoring_service.probe_address(server) == expected
    server.is_builtin = False
    assert monitoring_service.probe_address(server) == 'public.example.test'
