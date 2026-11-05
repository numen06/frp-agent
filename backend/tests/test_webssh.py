"""PTY passthrough, authorization and cleanup without accessing real hosts."""
import base64
import queue
import socket
import threading
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from starlette.websockets import WebSocketDisconnect

from app.auth import get_password_hash
from app.database import Base
from app.models.user import User
from app.models.managed_host import ManagedHost, HostAccessGrant, HostAuditLog
from app.models.ssh_credential import SshCredential
from app.services.credential_encryption import encrypt_secret
from app.routers import webssh
from app.webssh import app


class Channel:
    def __init__(self):
        self.messages = queue.Queue()
        self.inputs, self.sizes = [], []
        self.closed = False
        self.close_event = threading.Event()
        self.messages.put(b"\x1b[32mssh-ready\x1b[0m\r\n$ ")

    def settimeout(self, _): pass
    def set_combine_stderr(self, _): pass

    def recv(self, _):
        if self.closed: return b""
        try: return self.messages.get(timeout=.05)
        except queue.Empty: raise socket.timeout()

    def sendall(self, data):
        self.inputs.append(data)
        if data == b"exit\r": self.messages.put(b"")
        else: self.messages.put(data)

    def resize_pty(self, width, height): self.sizes.append((width, height))
    def close(self): self.closed = True; self.close_event.set(); self.messages.put(b"")


@pytest.fixture
def env(monkeypatch):
    engine = create_engine('sqlite://',connect_args={'check_same_thread':False},poolclass=StaticPool)
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    with factory() as db:
        password_hash = get_password_hash('demo-password')
        for name, role in [('operator','user'),('viewer','user'),('admin-webssh','admin')]:
            db.add(User(username=name,password_hash=password_hash,role=role,is_active=True))
        credential=SshCredential(name='demo',username='target-user',auth_type='password',password_encrypted=encrypt_secret('target-secret'))
        db.add(credential); db.flush()
        host=ManagedHost(name='ssh-demo',host_type='ssh',address='127.0.0.1',port=22,credential_id=credential.id,host_key_fingerprint='SHA256:pinned',is_active=True)
        db.add(host); db.flush()
        for username, execute in [('operator',True),('viewer',False)]:
            user=db.query(User).filter_by(username=username).one()
            db.add(HostAccessGrant(host_id=host.id,subject_type='user',subject_id=user.id,can_connect=True,can_execute=execute))
        db.commit(); host_id=host.id
    monkeypatch.setattr(webssh,'SessionLocal',factory)
    channels, clients = [], []
    real_build=webssh.build_host_client

    def build(host, credential):
        actual=real_build(host,credential)
        assert actual._expected_host_key == 'SHA256:pinned'
        assert actual._password == 'target-secret'
        channel=Channel(); channels.append(channel)
        client=SimpleNamespace(connect=lambda *args:None,open_shell=lambda *args:channel,close=channel.close)
        clients.append(client); return client
    monkeypatch.setattr(webssh,'build_host_client',build)
    webssh._sessions.clear(); webssh._pending=0
    with TestClient(app) as client:
        yield SimpleNamespace(client=client,factory=factory,channels=channels,clients=clients,id=host_id)
    assert webssh._pending == 0 and not webssh._sessions
    engine.dispose()


def auth(username='operator'):
    return dict(type='auth',authorization='Basic '+base64.b64encode(f'{username}:demo-password'.encode()).decode(),cols=90,rows=30)


def connect(env, origin='http://testserver'):
    return env.client.websocket_connect(f'/api/managed-hosts/{env.id}/terminal',headers={'origin':origin})


def output(ws):
    data = ws.receive_bytes()
    ws.send_json({'type': 'ack'})
    return data


def test_pty_input_unicode_resize_exit_and_audit(env):
    with connect(env) as ws:
        ws.send_json(auth()); assert ws.receive_json() == {'type':'ready'}
        assert b'ssh-ready' in output(ws)
        ws.send_json(dict(type='resize',cols=130,rows=42))
        text='echo 中文\r\x03'
        ws.send_json(dict(type='input',data=text))
        assert output(ws) == text.encode()
        ws.send_json(dict(type='input',data='exit\r'))
        assert ws.receive_json()['type'] == 'exit'
        assert ws.receive()['type'] == 'websocket.close'
    assert env.channels[0].closed and (130,42) in env.channels[0].sizes
    with env.factory() as db:
        rows=db.query(HostAuditLog).order_by(HostAuditLog.id).all()
        assert [r.action for r in rows] == ['webssh_connected','webssh_session']
        assert rows[-1].bytes_sent == len(text.encode())+5
        assert rows[-1].bytes_received > 0
        assert all(r.command is None and r.stdout is None for r in rows)
        assert all('target-secret' not in (r.stderr or '') for r in rows)


def test_cross_origin_and_connect_only_cannot_open_shell(env):
    with pytest.raises(WebSocketDisconnect):
        with connect(env,'https://attacker.invalid'): pass
    with connect(env) as ws:
        ws.send_json(auth('viewer'))
        assert 'execute' in ws.receive_json()['message']
    assert not env.channels


def test_no_url_auth_and_missing_pin_are_denied(env):
    with env.client.websocket_connect(f'/api/managed-hosts/{env.id}/terminal?api_key=not-accepted',headers={'origin':'http://testserver'}) as ws:
        ws.send_json(dict(type='auth'))
        assert ws.receive_json()['type'] == 'error'
    with env.factory() as db:
        db.get(ManagedHost,env.id).host_key_fingerprint=None; db.commit()
    with connect(env) as ws:
        ws.send_json(auth()); assert '指纹' in ws.receive_json()['message']
    assert not env.channels


def test_disconnect_and_revoked_access_close_resources(env,monkeypatch):
    monkeypatch.setattr(webssh,'CHECK_INTERVAL',.05)
    with connect(env) as ws:
        ws.send_json(auth()); assert ws.receive_json()['type']=='ready'; output(ws)
        with env.factory() as db:
            db.query(HostAccessGrant).filter_by(can_execute=True).delete(); db.commit()
        assert ws.receive_json()['type']=='error'
        assert ws.receive()['type']=='websocket.close'
    assert env.channels[-1].close_event.wait(2)
    with env.factory() as db:
        user=db.query(User).filter_by(username='operator').one()
        db.add(HostAccessGrant(host_id=env.id,subject_type='user',subject_id=user.id,can_execute=True,can_connect=True));db.commit()
    with connect(env) as ws:
        ws.send_json(auth()); assert ws.receive_json()['type']=='ready'; output(ws)
    assert env.channels[-1].close_event.wait(2)


def test_type_limits_and_fingerprint_errors(env,monkeypatch):
    monkeypatch.setattr(webssh,'MAX_PER_USER',0)
    with connect(env) as ws:
        ws.send_json(auth()); assert '上限' in ws.receive_json()['message']
    assert not env.channels
    monkeypatch.setattr(webssh,'MAX_PER_USER',4)
    def mismatch(*_): raise RuntimeError('SSH 主机指纹不匹配：expected vs actual')
    monkeypatch.setattr(webssh,'build_host_client',mismatch)
    with connect(env) as ws:
        ws.send_json(auth()); assert '指纹不匹配' in ws.receive_json()['message']


def test_failed_handshake_can_close_transport(monkeypatch):
    from app.services.ssh_client import ParamikoSSHClient
    closed=[]
    def fail(**kwargs): raise RuntimeError('test handshake failure')
    fake=SimpleNamespace(set_missing_host_key_policy=lambda _:None,connect=fail,close=lambda:closed.append(True))
    monkeypatch.setattr('app.services.ssh_client.paramiko.SSHClient',lambda:fake)
    client=ParamikoSSHClient(password='demo')
    with pytest.raises(RuntimeError):
        try: client.connect('localhost',22,'demo')
        finally: client.close()
    assert closed


def test_timeout_message_is_actionable(env,monkeypatch):
    closed=[]
    def timeout(*_): raise socket.timeout('timed out')
    monkeypatch.setattr(webssh,'build_host_client',lambda *_:SimpleNamespace(connect=timeout,close=lambda:closed.append(True)))
    with connect(env) as ws:
        ws.send_json(auth())
        assert '检查目标主机、网络及代理状态' in ws.receive_json()['message']
        assert ws.receive()['type']=='websocket.close'
    assert closed
