"""Built-in FRP onboarding, admin boundaries, rollback, and real process lifecycle."""
import asyncio
import os
from pathlib import Path
import socket
import socketserver
import subprocess
import threading
import time
import tomllib
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import httpx
import toml

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.auth import get_current_user
from app.config import get_settings
from app.database import Base, get_db
from app.frps_client import FrpsClient
from app.main import app
from app.models.builtin_frps import BuiltinFrpsConfig
from app.models.frps_server import FrpsServer
from app.models.user import User
from app.schemas.builtin_frps import BuiltinFrpsUpdate, BuiltinFrpsRawUpdate
from app.services.builtin_frps_service import BuiltinFrpsService, get_builtin_config, render_frps_config, runtime_config


@pytest.fixture
def setup(tmp_path, monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, 'builtin_frps_dir', str(tmp_path))
    monkeypatch.setattr(settings, 'ssh_credential_secret', 'builtin-frps-unit-test-secret')
    engine = create_engine('sqlite://', connect_args={'check_same_thread': False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        service = BuiltinFrpsService()
        try:
            yield db, service
        finally:
            service.stop()
            app.dependency_overrides.clear()
    engine.dispose()


def test_first_login_choice_persists_without_starting_frp(setup, monkeypatch):
    from app.routers import builtin_frps as router
    db, service = setup
    monkeypatch.setattr(router, 'builtin_frps_service', service)
    user = [User(id=1, username='admin', role='admin')]
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: user[0]
    client = TestClient(app)
    try:
        first = client.get('/api/builtin-frps')
        assert first.status_code == 200
        assert not first.json()['enabled'] and not first.json()['onboarding_seen']
        assert not db.get(BuiltinFrpsConfig, 1).token_encrypted
        assert not db.get(BuiltinFrpsConfig, 1).dashboard_password_encrypted
        assert 'auth_token' not in first.json() and 'dashboard_password' not in first.json()
        assert client.post('/api/builtin-frps/onboarding-seen').status_code == 200
        db.expire_all()
        again = client.get('/api/builtin-frps').json()
        assert again['onboarding_seen'] and not again['running'] and not again['enabled']
        assert db.get(BuiltinFrpsConfig, 1).onboarding_seen
        user[0] = User(id=2, username='member', role='user')
        for method, path in [('get', ''), ('post', '/onboarding-seen'), ('post', '/token'), ('post', '/restart')]:
            assert getattr(client, method)('/api/builtin-frps' + path).status_code == 403
        assert client.put('/api/builtin-frps', json={}).status_code == 403
    finally:
        client.close()


def test_toml_escapes_secrets_and_binds_management_to_loopback(setup):
    db, _ = setup
    config = runtime_config(get_builtin_config(db))
    config['auth_token'] = '令牌🔑long-token"\n[malicious]\nenabled=true'
    document = tomllib.loads(render_frps_config(config))
    assert document['auth']['token'] == config['auth_token']
    assert document['webServer']['addr'] == '127.0.0.1'
    assert 'malicious' not in document
    assert document['allowPorts'] == [{'start': 6000, 'end': 6099}]


def test_first_login_password_change_does_not_invalidate_unconfigured_frp(setup, monkeypatch):
    from app.services.credential_encryption import decrypt_secret
    db, service = setup
    monkeypatch.setattr(get_settings(), 'ssh_credential_secret', '')
    monkeypatch.setattr(get_settings(), 'auth_password', 'initial-password')
    config = get_builtin_config(db)
    assert not config.token_encrypted and not config.dashboard_password_encrypted
    monkeypatch.setattr(get_settings(), 'auth_password', 'changed-password')
    service.apply(db, BuiltinFrpsUpdate(enabled=False))
    assert decrypt_secret(config.token_encrypted)
    assert decrypt_secret(config.dashboard_password_encrypted)


def test_connection_token_is_generated_retained_and_user_editable(setup):
    from app.services.credential_encryption import decrypt_secret
    db, service = setup
    service.apply(db, BuiltinFrpsUpdate())
    config = db.get(BuiltinFrpsConfig, 1)
    generated = decrypt_secret(config.token_encrypted)
    assert generated and len(generated) >= 32
    service.apply(db, BuiltinFrpsUpdate())
    assert decrypt_secret(config.token_encrypted) == generated
    custom = 'user-defined-connection-token'
    service.apply(db, BuiltinFrpsUpdate(auth_token=custom))
    db.expire_all()
    assert runtime_config(db.get(BuiltinFrpsConfig, 1))['auth_token'] == custom
    service.apply(db, BuiltinFrpsUpdate())
    assert decrypt_secret(config.token_encrypted) == custom


@pytest.mark.parametrize('changes', [
    {'enabled': True}, {'public_addr': 'https://example.com/path'}, {'public_addr': 'a..com'},
    {'bind_port': 7500}, {'bind_port': 6001}, {'proxy_port_start': 6100},
    {'auth_token': 'short'}, {'dashboard_port': 0}, {'command': 'arbitrary'},
])
def test_invalid_and_conflicting_configuration_is_rejected(changes):
    with pytest.raises(ValidationError):
        BuiltinFrpsUpdate(**changes)


def test_failed_apply_keeps_saved_config_and_restores_previous_process(setup, monkeypatch):
    db, service = setup
    starts = []
    monkeypatch.setattr(service, '_write_config', lambda *a, **kw: None)
    monkeypatch.setattr(service, '_stop_process', lambda: None)
    def start(config):
        starts.append(config['bind_port'])
        if config['bind_port'] == 7100: raise ValueError('port already in use')
    monkeypatch.setattr(service, '_start_process', start)
    service.apply(db, BuiltinFrpsUpdate(enabled=True, public_addr='frp.test'))
    # The production path creates this on the first successful apply.
    service._config_path().write_text('original config', encoding='utf-8')
    with pytest.raises(ValueError, match='port already in use'):
        service.apply(db, BuiltinFrpsUpdate(enabled=True, public_addr='changed.test', bind_port=7100))
    assert starts[-2:] == [7100, 7000]
    assert db.get(BuiltinFrpsConfig, 1).bind_port == 7000
    assert db.query(FrpsServer).one().server_addr == 'frp.test'
    assert service._config_path().read_text() == 'original config'


def free_port():
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        return sock.getsockname()[1]


def test_existing_builtin_configuration_migrates_without_losing_settings(monkeypatch):
    from sqlalchemy import inspect, text
    from app.migrations import add_builtin_frps_field
    engine = create_engine('sqlite://')
    try:
        with engine.begin() as conn:
            conn.execute(text('CREATE TABLE frps_servers (id INTEGER PRIMARY KEY)'))
            conn.execute(text('CREATE TABLE builtin_frps_config (id INTEGER PRIMARY KEY, enabled BOOLEAN, bind_port INTEGER)'))
            conn.execute(text('INSERT INTO builtin_frps_config VALUES (1, 1, 7100)'))
        monkeypatch.setattr(add_builtin_frps_field, 'engine', engine)
        add_builtin_frps_field.upgrade()
        add_builtin_frps_field.upgrade()
        with engine.connect() as conn:
            assert conn.execute(text('SELECT enabled, bind_port, raw_config_encrypted FROM builtin_frps_config')).one() == (1, 7100, None)
            assert 'is_builtin' in {column['name'] for column in inspect(conn).get_columns('frps_servers')}
    finally:
        engine.dispose()


def test_builtin_port_pool_is_used_and_never_auto_expands(setup):
    from app.services.port_service import PortService
    db, _ = setup
    config = get_builtin_config(db)
    config.proxy_port_start, config.proxy_port_end = 18000, 18001
    server = FrpsServer(name='builtin', is_builtin=True, server_addr='frp.test', api_base_url='http://127.0.0.1/api', auth_username='u', auth_password='p')
    db.add(server); db.commit()
    ports = PortService(db)
    assert ports.get_next_available_port(server.id) == 18000
    ports.allocate_port(server.id, 18000, 'first')
    ports.allocate_port(server.id, 18001, 'second')
    assert ports.get_next_available_port(server.id) is None
    assert not ports.is_port_available(server.id, 18002)
    with pytest.raises(ValueError, match='18000'):
        ports.allocate_port(server.id, 18002, 'outside')
    ports.release_port(server.id, 18000)
    assert ports.get_next_available_port(server.id) == 18000


def test_raw_configuration_preserves_plugins_and_non_contiguous_port_pools(setup, monkeypatch):
    from app.services.port_service import PortService
    db, service = setup
    monkeypatch.setattr(service, '_write_config', lambda *a, **kw: None)
    service.apply(db, BuiltinFrpsUpdate())
    original = service.raw_document(db)
    document = tomllib.loads(original['content'])
    document['transport']['maxPoolCount'] = 13
    document['allowPorts'] = [{'single': 18000}, {'start': 19000, 'end': 19001}]
    document['httpPlugins'] = [dict(name='auth-plugin', addr='plugin:9000', path='/handler', ops=['Login'], tlsVerify=True)]
    content = '# keep this comment\n' + toml.dumps(document)
    service.apply(db, BuiltinFrpsRawUpdate(content=content, revision=original['revision']))
    assert service.raw_document(db)['content'] == content
    encrypted = db.get(BuiltinFrpsConfig, 1).raw_config_encrypted
    assert content not in encrypted and 'auth-plugin' not in encrypted
    service.apply(db, BuiltinFrpsUpdate(log_level='warn'))
    saved = tomllib.loads(service.raw_document(db)['content'])
    assert saved['httpPlugins'] == document['httpPlugins']
    assert saved['transport']['maxPoolCount'] == 13
    assert saved['allowPorts'] == document['allowPorts']
    with pytest.raises(ValueError, match='更新'):
        service.apply(db, BuiltinFrpsRawUpdate(content=content, revision=original['revision']))
    server = FrpsServer(name='builtin', is_builtin=True, server_addr='frp.test', api_base_url='http://127.0.0.1/api', auth_username='u', auth_password='p')
    db.add(server); db.commit()
    ports = PortService(db)
    assert ports.get_next_available_port(server.id) == 18000
    ports.allocate_port(server.id, 18000, 'one')
    assert ports.get_next_available_port(server.id) == 19000
    assert not ports.is_port_available(server.id, 18001)
    with pytest.raises(ValueError): ports.allocate_port(server.id, 18001, 'gap')


def test_raw_import_preserves_legacy_credentials_but_new_form_tokens_stay_strong(setup, monkeypatch):
    db, service = setup
    monkeypatch.setattr(service, '_write_config', lambda *a, **kw: None)
    document = tomllib.loads(service.raw_document(db)['content'])
    document['auth']['token'] = 'oldtoken'
    document['webServer']['password'] = 'oldpasswd'
    content = toml.dumps(document)
    service.apply(db, BuiltinFrpsRawUpdate(content=content))
    service.apply(db, BuiltinFrpsUpdate(log_level='warn'))
    values = runtime_config(db.get(BuiltinFrpsConfig, 1))
    assert values['auth_token'] == 'oldtoken' and values['dashboard_password'] == 'oldpasswd'
    assert tomllib.loads(service.raw_document(db)['content'])['log']['level'] == 'warn'
    with pytest.raises(ValidationError):
        BuiltinFrpsUpdate(auth_token='newshort')
    for path, value in [('token', ''), ('token', 'bad\nvalue'), ('password', '')]:
        invalid = tomllib.loads(content)
        invalid['auth' if path == 'token' else 'webServer'][path] = value
        with pytest.raises(ValueError):
            service.apply(db, BuiltinFrpsRawUpdate(content=toml.dumps(invalid)))


def test_raw_api_is_admin_only_and_does_not_cache_secrets(setup, monkeypatch):
    from app.routers import builtin_frps as router
    db, service = setup
    monkeypatch.setattr(router, 'builtin_frps_service', service)
    identity = [User(id=1, username='admin', role='admin')]
    app.dependency_overrides[get_current_user] = lambda: identity[0]
    app.dependency_overrides[get_db] = lambda: db
    client = TestClient(app)
    try:
        raw = client.get('/api/builtin-frps/raw-config')
        assert raw.status_code == 200 and raw.headers['cache-control'] == 'no-store'
        assert 'auth_token' not in client.get('/api/builtin-frps').json()
        assert 'content' not in client.get('/api/builtin-frps').json()
        content = raw.json()['content']
        unsafe = content.replace('addr = "127.0.0.1"', 'addr = "0.0.0.0"')
        assert client.put('/api/builtin-frps/raw-config', json={'content': unsafe}).status_code == 400
        identity[0] = User(id=2, username='member', role='user')
        assert client.get('/api/builtin-frps/raw-config').status_code == 403
        assert client.post('/api/builtin-frps/raw-config/preview', json={}).status_code == 403
        assert client.put('/api/builtin-frps/raw-config', json={'content': content}).status_code == 403
        assert client.post('/api/builtin-frps/raw-config/validate', json={'content': content}).status_code == 403
    finally:
        client.close()


@pytest.mark.skipif(not os.getenv('FRP_TEST_BINARY'), reason='Set FRP_TEST_BINARY to run with an official frps executable')
def test_real_frps_enable_restart_protect_registration_and_disable(setup, monkeypatch):
    from app.routers import builtin_frps as router
    db, service = setup
    monkeypatch.setattr(get_settings(), 'builtin_frps_binary', os.environ['FRP_TEST_BINARY'])
    monkeypatch.setattr(router, 'builtin_frps_service', service)
    ports = list({free_port() for _ in range(6)})[:3]
    data = BuiltinFrpsUpdate(enabled=True, public_addr='127.0.0.1', bind_port=ports[0], dashboard_port=ports[1], proxy_port_start=ports[2], proxy_port_end=ports[2])
    first = service.apply(db, data)
    assert first['running'] and first['server_id'] and first['version']
    pid = service._process.pid
    service.apply(db, data)
    assert service._process.pid != pid
    assert db.query(FrpsServer).count() == 1
    server = db.query(FrpsServer).one()
    info = asyncio.run(FrpsClient(server).get_server_info())
    assert info['version'] == first['version']
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: User(id=1, username='admin', role='admin')
    client = TestClient(app)
    try:
        assert client.put(f'/api/servers/{server.id}', json={'server_port': 1234}).status_code == 409
        assert client.delete(f'/api/servers/{server.id}').status_code == 409
        assert client.post('/api/builtin-frps/restart').status_code == 200
    finally:
        client.close()
    result = service.apply(db, data.model_copy(update={'enabled': False}))
    assert not result['running'] and not db.query(FrpsServer).one().is_active
    for port in ports[:2]:
        with socket.socket() as sock:
            sock.settimeout(0.2)
            assert sock.connect_ex(('127.0.0.1', port)) != 0


@pytest.mark.skipif(not (os.getenv('FRP_TEST_BINARY') and os.getenv('FRP_TEST_CLIENT_BINARY')), reason='Set FRP_TEST_BINARY and FRP_TEST_CLIENT_BINARY for a real transfer')
def test_generated_client_connects_and_real_port_traffic_is_synchronized(setup, monkeypatch, tmp_path):
    from app.models.proxy import Proxy
    from app.scheduler import sync_server
    from app.services.frpc_config_service import FrpcConfigService
    db, service = setup
    monkeypatch.setattr(get_settings(), 'builtin_frps_binary', os.environ['FRP_TEST_BINARY'])
    ports = list({free_port() for _ in range(6)})[:3]
    data = BuiltinFrpsUpdate(enabled=True, public_addr='127.0.0.1', bind_port=ports[0], dashboard_port=ports[1], proxy_port_start=ports[2], proxy_port_end=ports[2], auth_additional_scopes=['HeartBeats', 'NewWorkConns'])
    service.apply(db, data)
    server = db.query(FrpsServer).one()
    payload = bytes(range(256)) * 16
    class Echo(socketserver.BaseRequestHandler):
        def handle(self):
            while chunk := self.request.recv(65536):
                self.request.sendall(chunk)
    echo = socketserver.ThreadingTCPServer(('127.0.0.1', 0), Echo)
    echo.daemon_threads = True
    threading.Thread(target=echo.serve_forever, daemon=True).start()
    proxy = Proxy(name='integration_echo', group_name='integration', frps_server_id=server.id,
                  local_port=echo.server_address[1], local_ip='127.0.0.1', remote_port=ports[2], proxy_type='tcp')
    db.add(proxy); db.commit()
    config = tmp_path / 'client.toml'
    generated = FrpcConfigService(db).generate_config_for_group('integration', server.id, format='toml')
    document = tomllib.loads(generated)
    assert document['auth']['additionalScopes'] == ['HeartBeats', 'NewWorkConns']
    assert document['transport']['tls']['enable'] is True
    config.write_text(generated, encoding='utf-8')
    client = subprocess.Popen([os.environ['FRP_TEST_CLIENT_BINARY'], '-c', str(config)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                              creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
    try:
        deadline = time.monotonic() + 10
        while True:
            try:
                connection = socket.create_connection(('127.0.0.1', ports[2]), timeout=0.5)
                break
            except OSError:
                assert time.monotonic() < deadline and client.poll() is None
                time.sleep(0.1)
        with connection:
            connection.settimeout(3)
            connection.sendall(payload)
            received = bytearray()
            while len(received) < len(payload):
                received.extend(connection.recv(65536))
            assert bytes(received) == payload
        deadline = time.monotonic() + 8
        while True:
            asyncio.run(sync_server(db, server))
            db.refresh(proxy)
            if proxy.today_traffic_in and proxy.today_traffic_out:
                break
            assert time.monotonic() < deadline
            time.sleep(0.2)
        assert proxy.today_traffic_in >= len(payload)
        assert proxy.today_traffic_out >= len(payload)
        assert proxy.status == 'online'
    finally:
        client.terminate(); client.wait(timeout=5)
        echo.shutdown(); echo.server_close()


@pytest.mark.skipif(not (os.getenv('FRP_TEST_BINARY') and os.getenv('FRP_TEST_CLIENT_BINARY')), reason='Requires official frps and frpc executables')
def test_real_default_security_without_editing_a_raw_config(setup, monkeypatch, tmp_path):
    db, service = setup
    monkeypatch.setattr(get_settings(), 'builtin_frps_binary', os.environ['FRP_TEST_BINARY'])
    control, dashboard, allowed, forbidden = list({free_port() for _ in range(8)})[:4]
    service.apply(db, BuiltinFrpsUpdate(enabled=True, public_addr='127.0.0.1', bind_port=control,
                                      dashboard_port=dashboard, proxy_port_start=allowed, proxy_port_end=allowed))
    # All security settings above are defaults; only ephemeral test ports/address differ.
    config = runtime_config(db.get(BuiltinFrpsConfig, 1))
    document = tomllib.loads(service.raw_document(db)['content'])
    assert len(config['auth_token']) >= 32 and config['auth_token'] != config['dashboard_password']
    assert document['transport']['tls']['force'] is True
    assert document['webServer']['addr'] == '127.0.0.1'
    assert not document['webServer']['pprofEnable'] and not document['detailedErrorsToClient']
    assert not document.get('httpPlugins') and not document.get('kcpBindPort') and not document.get('quicBindPort')
    with httpx.Client(timeout=2, trust_env=False) as http:
        api = f'http://127.0.0.1:{dashboard}/api/serverinfo'
        assert http.get(api).status_code == 401
        assert http.get(api, auth=('frp-agent', 'incorrect')).status_code == 401
        assert http.get(api, auth=('frp-agent', config['dashboard_password'])).status_code == 200
    for address in {info[4][0] for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET)}:
        if not address.startswith('127.'):
            with socket.socket() as sock:
                sock.settimeout(.3)
                assert sock.connect_ex((address, dashboard)) != 0
    server = db.query(FrpsServer).one()
    for case in ('valid', 'wrong-token', 'plaintext', 'forbidden-port'):
        name = 'security_' + case
        client_document = {
            'serverAddr': '127.0.0.1', 'serverPort': control, 'loginFailExit': True,
            'auth': {'token': config['auth_token'] if case != 'wrong-token' else 'a-deliberately-wrong-token'},
            'transport': {'tls': {'enable': case != 'plaintext'}},
            'proxies': [dict(name=name, type='tcp', localIP='127.0.0.1', localPort=9,
                             remotePort=forbidden if case == 'forbidden-port' else allowed)],
        }
        path = tmp_path / (case + '.toml'); path.write_text(toml.dumps(client_document), encoding='utf-8')
        output = tmp_path / (case + '.log')
        with output.open('w', encoding='utf-8') as log:
            client = subprocess.Popen([os.environ['FRP_TEST_CLIENT_BINARY'], '-c', str(path)], stdout=log, stderr=subprocess.STDOUT,
                                      creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
            try:
                deadline = time.monotonic() + 8
                while True:
                    proxy = asyncio.run(FrpsClient(server).get_proxy_by_name(name))
                    logs = output.read_text(encoding='utf-8', errors='replace')
                    if case == 'valid' and proxy and proxy.get('status') == 'online': break
                    if case in {'wrong-token', 'plaintext'} and client.poll() is not None: break
                    if case == 'forbidden-port' and 'start error' in logs.lower(): break
                    assert time.monotonic() < deadline, f'{case} did not reach the expected result: {logs}'
                    time.sleep(.1)
                if case != 'valid':
                    assert not proxy or proxy.get('status') != 'online'
                if case in {'wrong-token', 'plaintext'}: assert client.returncode != 0
                if case == 'forbidden-port':
                    with socket.socket() as sock:
                        sock.settimeout(.2)
                        assert sock.connect_ex(('127.0.0.1', forbidden)) != 0
                assert service.running
            finally:
                if client.poll() is None: client.terminate()
                client.wait(timeout=5)


@pytest.mark.skipif(not (os.getenv('FRP_TEST_BINARY') and os.getenv('FRP_TEST_CLIENT_BINARY')), reason='Requires official frps and frpc executables')
def test_real_plugin_callbacks_raw_edit_validation_and_restore(setup, monkeypatch, tmp_path):
    db, service = setup
    monkeypatch.setattr(get_settings(), 'builtin_frps_binary', os.environ['FRP_TEST_BINARY'])
    calls = []
    class Plugin(BaseHTTPRequestHandler):
        def do_POST(self):
            payload = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
            calls.append((self.path, payload))
            denied = payload.get('content', {}).get('proxy_name') == 'plugin-denied'
            response = json.dumps({'reject': True, 'reject_reason': 'blocked by test plugin'} if denied else {'reject': False, 'unchange': True}).encode()
            self.send_response(200); self.send_header('Content-Length', str(len(response))); self.end_headers(); self.wfile.write(response)
        def log_message(self, *args): pass
    plugin = ThreadingHTTPServer(('127.0.0.1', 0), Plugin)
    threading.Thread(target=plugin.serve_forever, daemon=True).start()
    control, dashboard, remote = list({free_port() for _ in range(8)})[:3]
    try:
        service.apply(db, BuiltinFrpsUpdate(enabled=True, public_addr='127.0.0.1', bind_port=control, dashboard_port=dashboard,
                                          proxy_port_start=remote, proxy_port_end=remote,
                                          http_plugins=[dict(name='policy', addr=f'127.0.0.1:{plugin.server_port}', ops=['Login', 'NewProxy'])],
                                          auth_additional_scopes=['HeartBeats', 'NewWorkConns']))
        original = service.raw_document(db)
        document = tomllib.loads(original['content'])
        document['transport']['maxPoolCount'] = 11
        content = '# preserved raw plugin configuration\n' + toml.dumps(document)
        request = BuiltinFrpsRawUpdate(enabled=True, public_addr='127.0.0.1', content=content, revision=original['revision'])
        pid = service._process.pid
        assert service.validate_raw(request) == {'valid': True}
        assert service._process.pid == pid and service.raw_document(db)['content'] == original['content']
        service.apply(db, request)
        assert service._config_path().read_bytes() == content.encode('utf-8')
        current_pid = service._process.pid
        with pytest.raises(ValueError):
            service.apply(db, BuiltinFrpsRawUpdate(enabled=True, public_addr='127.0.0.1', content='invalid = [', revision=service.raw_document(db)['revision']))
        invalid_document = tomllib.loads(content)
        invalid_document['unsupportedServerOption'] = True
        with pytest.raises(ValueError, match='校验'):
            service.apply(db, BuiltinFrpsRawUpdate(enabled=True, public_addr='127.0.0.1', content=toml.dumps(invalid_document)))
        assert service._process.pid == current_pid and service.running
        assert service.raw_document(db)['content'] == content
        service.apply(db, BuiltinFrpsUpdate(log_level='warn'))
        saved = service.raw_document(db)['content']
        assert tomllib.loads(saved)['httpPlugins'] == document['httpPlugins']
        assert tomllib.loads(saved)['transport']['maxPoolCount'] == 11
        service.stop(); service.restore(db)
        assert service.running and service.raw_document(db)['content'] == saved
        config = runtime_config(db.get(BuiltinFrpsConfig, 1))
        for name in ('plugin-allowed', 'plugin-denied'):
            client_document = dict(serverAddr='127.0.0.1', serverPort=control, loginFailExit=True,
                                   auth=dict(token=config['auth_token'], additionalScopes=['HeartBeats', 'NewWorkConns']),
                                   transport={'tls': {'enable': True}},
                                   proxies=[dict(name=name, type='tcp', localIP='127.0.0.1', localPort=9, remotePort=remote)])
            path = tmp_path / (name + '.toml'); path.write_text(toml.dumps(client_document), encoding='utf-8')
            client = subprocess.Popen([os.environ['FRP_TEST_CLIENT_BINARY'], '-c', str(path)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                      creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
            try:
                deadline = time.monotonic() + 8
                while not any('op=NewProxy' in url and body['content']['proxy_name'] == name for url, body in calls):
                    assert time.monotonic() < deadline
                    time.sleep(.1)
                server = db.query(FrpsServer).one()
                deadline = time.monotonic() + 5
                while True:
                    item = asyncio.run(FrpsClient(server).get_proxy_by_name(name))
                    if name == 'plugin-denied':
                        assert not item or item.get('status') != 'online'; break
                    if item and item.get('status') == 'online': break
                    assert time.monotonic() < deadline
                    time.sleep(.1)
            finally:
                client.terminate(); client.wait(timeout=5)
        assert any('op=Login' in url for url, _ in calls)
    finally:
        plugin.shutdown(); plugin.server_close()
