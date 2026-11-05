"""Isolated VNC protocol, authorization, revocation and secret-boundary tests."""
import base64
import struct
import time
from types import SimpleNamespace
import pytest
from fastapi import HTTPException
from starlette.websockets import WebSocketDisconnect
from app.models.managed_host import ManagedHost, HostAccessGrant, HostAuditLog
from app.models.ssh_credential import SshCredential
from app.models.user import User
from app.services.credential_encryption import encrypt_secret
from app.services import vnc_service as service
from app.routers import webvnc
from test_webssh import env, auth, Channel

INITIAL = struct.pack('!HH', 16, 16) + bytes([32,24,0,1]) + struct.pack('!HHH',255,255,255) + bytes([16,8,0,0,0,0]) + struct.pack('!I',4) + b'demo'

class Handshake:
    def __init__(self, data): self.data=bytearray(data); self.sent=[]
    def settimeout(self, _): pass
    def recv(self, n):
        n=min(n,3); result=bytes(self.data[:n]);del self.data[:n];return result
    def sendall(self, data): self.sent.append(data)

@pytest.mark.parametrize('banner,security',[(b'RFB 003.003\n',struct.pack('!I',2)),(b'RFB 003.007\n',b'\x01\x02'),(b'RFB 003.008\n',b'\x02\x01\x02'),(b'RFB 003.889\n',b'\x01\x02')])
def test_password_handshake_fragmentation(banner,security):
    h=Handshake(banner+security+bytes(range(16))+b'\0'*4+INITIAL)
    assert service.authenticate_vnc(h,'secret')==INITIAL
    assert b'secret' not in b''.join(h.sent)
    assert h.sent[-1]==b'\x01'

@pytest.mark.parametrize('data',[b'RFB 003.008\n\x01\x01',b'RFB 003.003\n'+struct.pack('!I',1),b'bad protocol'])
def test_reject_no_auth_or_invalid_protocol(data):
    with pytest.raises(ValueError): service.authenticate_vnc(Handshake(data),'secret')

def test_bad_password_and_oversized_desktop():
    with pytest.raises(ValueError,match='密码'):
        service.authenticate_vnc(Handshake(b'RFB 003.008\n\x01\x02'+b'x'*16+b'\0\0\0\x01'),'secret')
    data=INITIAL[:20]+struct.pack('!I',999999)
    with pytest.raises(ValueError,match='超出'):
        service.authenticate_vnc(Handshake(b'RFB 003.008\n\x01\x02'+b'x'*16+b'\0'*4+data),'secret')

@pytest.fixture
def vnc_env(env, monkeypatch):
    with env.factory() as db:
        credential=SshCredential(name='vnc-pass',username='vnc',auth_type='password',password_encrypted=encrypt_secret('secret'))
        db.add(credential);db.flush()
        host=ManagedHost(name='mac-vnc',host_type='vnc',address='127.0.0.1',port=5900,vnc_ssh_host_id=env.id,credential_id=credential.id,is_active=True)
        db.add(host);db.flush()
        operator=db.query(User).filter_by(username='operator').one()
        db.add(HostAccessGrant(host_id=host.id,subject_type='user',subject_id=operator.id,can_connect=True,can_execute=False))
        db.commit(); host_id=host.id
    monkeypatch.setattr(webvnc,'SessionLocal',env.factory)
    monkeypatch.setattr(webvnc,'CHECK_INTERVAL',.05)
    channels=[]
    def open_vnc(db,host):
        service.snapshot(db,host)
        channel=Channel();channel.messages.get(); channels.append(channel)
        return SimpleNamespace(close=channel.close),channel,INITIAL
    monkeypatch.setattr(webvnc,'open_vnc',open_vnc)
    webvnc._sessions.clear();webvnc._pending=0
    yield SimpleNamespace(**vars(env),vnc_id=host_id,vnc_channels=channels)
    assert webvnc._pending==0 and not webvnc._sessions

def connect(env, origin='https://testserver', scheme='wss'):
    return env.client.websocket_connect(f'{scheme}://testserver/api/managed-hosts/{env.vnc_id}/vnc',headers={'origin':origin})

def handshake(ws):
    ws.send_json(auth()); assert ws.receive_json()['type']=='ready'
    assert ws.receive_bytes()==b'RFB 003.008\n'
    ws.send_bytes(b'RFB 003.008\n');assert ws.receive_bytes()==b'\x01\x01'
    ws.send_bytes(b'\x01');assert ws.receive_bytes()==b'\0'*4
    ws.send_bytes(b'\x01');assert ws.receive_bytes()==INITIAL

def test_bridge_and_audit_no_secrets(vnc_env):
    e=vnc_env
    with connect(e) as ws:
        handshake(ws)
        ws.send_bytes(b'pointer-event'); assert ws.receive_bytes()==b'pointer-event'
        e.vnc_channels[-1].messages.put(b'')
        assert ws.receive()['type']=='websocket.close'
    assert e.vnc_channels[-1].close_event.wait(2)
    with e.factory() as db:
        logs=db.query(HostAuditLog).filter_by(host_id=e.vnc_id).all()
        assert {x.action for x in logs}=={'vnc_connected','vnc_session'}
        assert all('secret' not in str(vars(x)) for x in logs)

def test_origin_tls_authorization_and_capacity(vnc_env,monkeypatch):
    e=vnc_env
    for origin,scheme in [('https://evil.example','wss'),('http://testserver','ws')]:
        with pytest.raises(WebSocketDisconnect):
            with connect(e,origin,scheme): pass
    with connect(e) as ws:
        ws.send_json(auth('viewer'));assert ws.receive_json()['type']=='error'
    assert not e.vnc_channels
    monkeypatch.setattr(webvnc,'MAX_PER_USER',0)
    with connect(e) as ws:
        ws.send_json(auth());assert '上限' in ws.receive_json()['message']
    assert not e.vnc_channels

def test_revocation_and_credential_rotation(vnc_env):
    e=vnc_env
    with connect(e) as ws:
        handshake(ws)
        ws.send_bytes(b'check'); assert ws.receive_bytes()==b'check'
        with e.factory() as db:
            db.query(HostAccessGrant).filter_by(host_id=e.vnc_id).delete();db.commit()
        assert ws.receive()['type']=='websocket.close'
    assert e.vnc_channels[-1].close_event.wait(2)

def test_validation_rejects_unpinned_or_remote_destination(vnc_env):
    e=vnc_env
    with e.factory() as db:
        host=db.get(ManagedHost,e.vnc_id)
        values=dict(address='192.168.1.2',credential_id=host.credential_id,vnc_ssh_host_id=e.id)
        with pytest.raises(HTTPException):service.validate_vnc_values(db,values)
        values['address']='127.0.0.1'
        db.get(ManagedHost,e.id).host_key_fingerprint=None
        with pytest.raises(HTTPException):service.validate_vnc_values(db,values)

def test_crud_defaults_reference_guard_and_no_secret_response(vnc_env):
    from app.routers.managed_host import create_host, update_host, delete_host
    from app.schemas.managed_host import ManagedHostCreate, ManagedHostUpdate
    e=vnc_env
    with e.factory() as db:
        admin=db.query(User).filter_by(username='admin-webssh').one()
        original=db.get(ManagedHost,e.vnc_id)
        body=ManagedHostCreate(name='another-mac',host_type='vnc',address='127.0.0.1',credential_id=original.credential_id,vnc_ssh_host_id=e.id)
        assert body.port==5900
        response=create_host(body,db,admin)
        assert response.credential_kind=='VNC' and response.vnc_ssh_host_id==e.id
        assert 'secret' not in response.model_dump_json()
        updated=update_host(response.id,ManagedHostUpdate(description='updated'),db,admin)
        assert updated.vnc_ssh_host_id==e.id and updated.description=='updated'
        with pytest.raises(HTTPException) as exc: delete_host(e.id,db,admin)
        assert exc.value.status_code==409
        viewer=db.query(User).filter_by(username='viewer').one()
        with pytest.raises(HTTPException) as exc: create_host(body,db,viewer)
        assert exc.value.status_code==403
        delete_host(response.id,db,admin)

def test_credential_changes_revoke_session(vnc_env):
    e=vnc_env
    with connect(e) as ws:
        handshake(ws)
        ws.send_bytes(b'check');assert ws.receive_bytes()==b'check'
        with e.factory() as db:
            host=db.get(ManagedHost,e.vnc_id)
            host.credential.password_encrypted=encrypt_secret('changed');db.commit()
        assert ws.receive()['type']=='websocket.close'

def test_existing_database_migration_is_repeatable(monkeypatch):
    from sqlalchemy import create_engine, text, inspect
    from app.database import Base
    from app.migrations import add_host_management_tables as migration
    engine=create_engine('sqlite://')
    Base.metadata.create_all(engine)
    with engine.begin() as conn:
        conn.execute(text('ALTER TABLE managed_hosts DROP COLUMN vnc_ssh_host_id'))
        conn.execute(text("INSERT INTO managed_hosts (name,address,port,host_type,docker_use_tls,docker_verify_tls,is_active,last_status,created_at,updated_at) VALUES ('existing','localhost',22,'ssh',1,1,1,'unknown',CURRENT_TIMESTAMP,CURRENT_TIMESTAMP)"))
    monkeypatch.setattr(migration,'engine',engine)
    migration.upgrade();migration.upgrade()
    assert 'vnc_ssh_host_id' in {x['name'] for x in inspect(engine).get_columns('managed_hosts')}
    with engine.connect() as conn:
        assert conn.execute(text("SELECT name,vnc_ssh_host_id FROM managed_hosts")).one()==('existing',None)
    engine.dispose()
