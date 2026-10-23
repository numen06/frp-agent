"""Traffic is counted in bytes at the transport boundary and isolated by actor."""
import asyncio
from contextlib import closing
import io
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.auth import get_current_user
from app.database import Base, get_db
from app.frps_client import FrpsClient
from app.main import app
from app.models.frps_server import FrpsServer
from app.models.managed_host import HostAuditLog, ManagedHost
from app.models.proxy import Proxy
from app.models.user import User
from app.services.host_access_service import add_audit_log, list_docker_containers
from app.services.ssh_client import CommandResult, ParamikoSSHClient
from app.services.ssh_gateway_service import _bridge_channels


def test_command_counts_raw_bytes_before_decoding_and_trimming():
    raw_out, raw_err = ' 中文 \n'.encode(), b'\xff\n'
    stdout, stderr, stdin = io.BytesIO(raw_out), io.BytesIO(raw_err), io.StringIO()
    stdout.channel = SimpleNamespace(recv_exit_status=lambda: 0)
    stdin.channel = SimpleNamespace(shutdown_write=lambda: None)
    client = ParamikoSSHClient()
    client._client = SimpleNamespace(exec_command=lambda *a, **kw: (stdin, stdout, stderr))
    result = client.exec_command('echo 中文', stdin_data='输入\n')
    assert result.stdout == '中文'
    assert result.bytes_sent == len('echo 中文输入\n'.encode())
    assert result.bytes_received == len(raw_out) + len(raw_err)


def test_ssh_bridge_counts_binary_sftp_and_partial_stderr_writes():
    class Channel:
        def __init__(self, data, errors=()):
            self.data, self.errors = iter(data), iter(errors)
            self.sent, self.stderr = b'', b''
        def recv(self, size): return next(self.data, b'')
        def recv_stderr(self, size): return next(self.errors, b'')
        def sendall(self, data): self.sent += data
        def send_stderr(self, data):
            self.stderr += data[:2]
            return min(2, len(data))
        def shutdown_read(self): pass
        def shutdown_write(self): pass
    inbound = Channel([b'\x00\xff\x00', '输入'.encode()])
    upstream = Channel([b'\x80\x00', '输出'.encode()], [b'error\n'])
    traffic = dict(bytes_sent=0, bytes_received=0)
    _bridge_channels(inbound, upstream, traffic)
    assert upstream.sent == b'\x00\xff\x00' + '输入'.encode()
    assert inbound.sent == b'\x80\x00' + '输出'.encode()
    assert inbound.stderr == b'error\n'
    assert traffic == dict(bytes_sent=len(upstream.sent), bytes_received=len(inbound.sent) + len(inbound.stderr))


def test_traffic_summary_is_scoped_filtered_and_not_limited_to_one_page():
    engine = create_engine('sqlite://', connect_args={'check_same_thread': False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        admin = User(id=1, username='admin', password_hash='x', role='admin')
        member = User(id=2, username='member', password_hash='x', role='user')
        key = User(id=-3, username='key', password_hash='', role='user')
        host = ManagedHost(name='host', address='host.test', host_type='ssh')
        db.add_all([admin, member, host]); db.commit()
        for _ in range(25):
            add_audit_log(db, host, member, 'ssh_gateway_session', 'success', '192.0.2.1', bytes_sent=2**32, bytes_received=7)
        add_audit_log(db, host, admin, 'execute_command', 'failed', '192.0.2.2', result=CommandResult(1, '', '', 10, 20))
        add_audit_log(db, host, key, 'ssh_gateway_session', 'success', '192.0.2.3', bytes_sent=30, bytes_received=40)
        legacy = add_audit_log(db, host, member, 'connection_test', 'success', None)
        assert legacy.bytes_sent is None and legacy.bytes_received is None
        identity = [member]
        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[get_current_user] = lambda: identity[0]
        try:
            with closing(TestClient(app)) as client:
                result = client.get('/api/managed-hosts/audit/traffic').json()
                assert result == dict(bytes_sent=25 * 2**32, bytes_received=175, measured_count=25, record_count=26)
                logs = client.get('/api/managed-hosts/audit/logs', params={'page': 1, 'page_size': 5}).json()
                assert len(logs['items']) == 5
                assert logs['items'][0]['bytes_sent'] is None
                identity[0] = key
                assert client.get('/api/managed-hosts/audit/traffic').json()['bytes_received'] == 40
                identity[0] = admin
                assert client.get('/api/managed-hosts/audit/traffic', params={'status': 'failed'}).json()['bytes_sent'] == 10
                assert client.get('/api/managed-hosts/audit/traffic', params={'host_id': 999}).json()['record_count'] == 0
                assert client.get('/api/managed-hosts/audit/traffic', params={'search': '192.0.2.3'}).json()['bytes_sent'] == 30
                assert client.get('/api/managed-hosts/audit/traffic', params={'start_time': '2026-01-02', 'end_time': '2026-01-01'}).status_code == 422
        finally:
            app.dependency_overrides.clear()
    engine.dispose()


@pytest.mark.parametrize('flow', ['scheduler', 'compare', 'list'])
def test_all_frp_sync_paths_save_snapshots_without_double_counting(monkeypatch, flow):
    engine = create_engine('sqlite://')
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        server = FrpsServer(name='test', server_addr='127.0.0.1', api_base_url='http://127.0.0.1/api', auth_username='u', auth_password='p')
        db.add(server); db.commit()
        raw = dict(name='test_tcp', status='online', conf={'remotePort': 6010}, todayTrafficIn=2**34, todayTrafficOut=9876, curConns=2)
        async def proxies(self): return {'tcp': [raw]}
        async def version(self): return '0.71.1'
        monkeypatch.setattr(FrpsClient, 'get_all_proxies', proxies)
        monkeypatch.setattr(FrpsClient, 'get_server_version', version)
        user = User(id=1, username='admin', role='admin')
        async def sync():
            if flow == 'scheduler':
                from app.scheduler import sync_server
                await sync_server(db, server)
            elif flow == 'compare':
                from app.routers.sync import compare_proxies
                await compare_proxies(server.id, True, db, user)
            else:
                from app.routers.proxy import get_proxies
                await get_proxies(server.id, None, None, None, 1, 20, True, db, user)
        asyncio.run(sync()); asyncio.run(sync())
        proxy = db.query(Proxy).one()
        assert proxy.today_traffic_in == 2**34 and proxy.today_traffic_out == 9876
        assert proxy.cur_conns == 2 and proxy.traffic_updated_at is not None
        raw['todayTrafficIn'] = 5  # frps restart/day boundary: replace the snapshot.
        asyncio.run(sync())
        assert proxy.today_traffic_in == 5
        raw.pop('todayTrafficOut')
        asyncio.run(sync())
        assert proxy.today_traffic_out is None  # An absent metric is not zero.


def test_traffic_migration_is_idempotent_and_keeps_unknown_data_null(monkeypatch):
    from app.migrations import add_traffic_fields
    engine = create_engine('sqlite://')
    with engine.begin() as conn:
        conn.execute(text('CREATE TABLE proxies (id INTEGER PRIMARY KEY)'))
        conn.execute(text('CREATE TABLE host_audit_logs (id INTEGER PRIMARY KEY)'))
        conn.execute(text('INSERT INTO host_audit_logs VALUES (1)'))
    monkeypatch.setattr(add_traffic_fields, 'engine', engine)
    add_traffic_fields.upgrade(); add_traffic_fields.upgrade()
    assert 'traffic_updated_at' in {c['name'] for c in inspect(engine).get_columns('proxies')}
    with engine.connect() as conn:
        assert conn.execute(text('SELECT bytes_sent, bytes_received FROM host_audit_logs')).one() == (None, None)
