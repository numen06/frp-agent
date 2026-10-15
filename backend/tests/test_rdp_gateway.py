"""Native RDP gateway authentication, stored credentials and revocation boundaries."""
from datetime import datetime,timedelta
from unittest.mock import Mock
import hashlib,time
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from starlette.requests import Request
from app.auth import authenticate_user,get_current_user,get_password_hash
from app.config import get_settings
from app.database import Base,get_db
from app.main import app
from app.models.api_key import ApiKey
from app.models.managed_host import HostAccessGrant,HostAuditLog,ManagedHost
from app.models.ssh_credential import SshCredential
from app.models.user import User
from app.services.credential_encryption import encrypt_secret
from app.services.rdp_gateway_service import RDPGatewayService,Relay,rdp_client_ip,require_secure_rdp_download,rdp_credential
from app.services import rdp_gateway_service as module
from app.services.rdp_auth_service import ntlm_verifier

@pytest.fixture
def setup(monkeypatch):
    settings=get_settings()
    monkeypatch.setattr(settings,'rdp_gateway_enabled',True)
    monkeypatch.setattr(settings,'rdp_gateway_public_address','rdp.example.test:13389')
    monkeypatch.setattr(settings,'rdp_gateway_trusted_proxies','')
    engine=create_engine('sqlite://',connect_args={'check_same_thread':False},poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with sessionmaker(bind=engine)() as db:
        credential=SshCredential(name='Windows login',username='WIN-TEST\\administrator',auth_type='password',password_encrypted=encrypt_secret('windows-test-password'))
        user=User(username='rdp-user',password_hash=get_password_hash('platform-test-password'),role='user',is_active=True)
        host=ManagedHost(name='win-1',host_type='rdp',address='win.internal',port=3389,credential=credential,host_key_fingerprint='SHA256:'+'a'*64)
        db.add_all([user,host]);db.commit()
        grant=HostAccessGrant(host_id=host.id,subject_type='user',subject_id=user.id,can_connect=True,can_execute=False)
        db.add(grant);db.commit()
        service=RDPGatewayService();service._process=Mock(poll=lambda:None);service._listener=Mock()
        service._sessions[12345]=Relay(ip='198.51.100.10',sockets=())
        yield db,user,host,grant,service
    engine.dispose()

def login(setup):
    db,user,host,_,service=setup
    return service.authorize(db,12345,user.username+'#'+host.name,'platform-test-password')

def test_platform_login_maps_to_separate_encrypted_windows_credential(setup):
    db,user,host,grant,service=setup
    result=login(setup)
    assert result==dict(address='win.internal',port=3389,username='administrator',domain='WIN-TEST',password='windows-test-password',fingerprint='a'*64)
    assert host.credential.password_encrypted!='windows-test-password'
    assert service._sessions[12345].authorized
    assert not service._sessions[12345].connected
    assert db.query(HostAuditLog).one().action=='rdp_gateway_authorized'
    service.authorize(db,12345,'','','connected')
    assert service._sessions[12345].connected
    assert db.query(HostAuditLog).order_by(HostAuditLog.id.desc()).first().action=='rdp_desktop_connected'

@pytest.mark.parametrize('change',['wrong_password','missing_grant','host_disabled','user_disabled','wrong_host_type','expired_grant'])
def test_unauthorized_logins_never_receive_target_credentials(setup,change):
    db,user,host,grant,service=setup
    password='platform-test-password'
    if change=='wrong_password':password='wrong'
    if change=='missing_grant':grant.is_active=False
    if change=='host_disabled':host.is_active=False
    if change=='user_disabled':user.is_active=False
    if change=='wrong_host_type':host.host_type='ssh'
    if change=='expired_grant':grant.expires_at=datetime.utcnow()-timedelta(seconds=1)
    db.commit()
    with pytest.raises(HTTPException):service.authorize(db,12345,user.username+'#'+host.name,password)
    assert not service._sessions[12345].authorized

def test_admin_uses_same_platform_login_without_explicit_grant(setup):
    db,user,host,grant,service=setup
    user.role='admin';grant.is_active=False;db.commit()
    assert login(setup)['username']=='administrator'

def test_api_key_login_requires_rdp_connect_grant(setup):
    db,user,host,grant,service=setup
    raw='key-for-test'
    key=ApiKey(key=hashlib.sha256(raw.encode()).hexdigest(),description='test',is_active=True)
    db.add(key);db.commit()
    with pytest.raises(HTTPException):service.authorize(db,12345,host.name,raw)
    db.add(HostAccessGrant(host_id=host.id,subject_type='api_key',subject_id=key.id,can_connect=True));db.commit()
    assert service.authorize(db,12345,host.name,raw)['username']=='administrator'
    assert service._sessions[12345].uid==-key.id

@pytest.mark.parametrize('change',['grant','user','platform_password','host','address','windows_password','certificate','credential'])
def test_live_session_is_revoked_when_authorization_or_credentials_change(setup,change):
    db,user,host,grant,service=setup;login(setup)
    if change=='grant':grant.is_active=False
    if change=='user':user.is_active=False
    if change=='platform_password':user.password_hash='changed'
    if change=='host':host.is_active=False
    if change=='address':host.address='another.internal'
    if change=='windows_password':host.credential.password_encrypted=encrypt_secret('changed')
    if change=='certificate':host.host_key_fingerprint='SHA256:'+'b'*64
    if change=='credential':host.credential=None
    db.commit()
    with pytest.raises(HTTPException):service._validate(db,service._sessions[12345])

def test_login_is_bound_to_an_active_frontend_connection(setup):
    db,user,host,_,service=setup
    with pytest.raises(HTTPException):service.authorize(db,54321,user.username+'#'+host.name,'platform-test-password')
    with pytest.raises(HTTPException):service.authorize(db,12345,'','','connected')
    service._sessions[12345].created-=21
    with pytest.raises(HTTPException):login(setup)

def test_login_cannot_be_reused_on_the_same_connection(setup):
    login(setup)
    with pytest.raises(HTTPException):login(setup)

@pytest.mark.parametrize('pin',[None,'SHA256:short','SHA256:'+'g'*64])
def test_target_certificate_is_required(setup,pin):
    db,user,host,_,service=setup;host.host_key_fingerprint=pin
    with pytest.raises(HTTPException):login(setup)

def test_private_keys_cannot_be_used_as_windows_passwords(setup):
    db,user,host,_,service=setup;host.credential.auth_type='private_key'
    with pytest.raises(HTTPException):rdp_credential(host)

def test_rdp_file_contains_only_platform_login_and_public_endpoint(setup):
    db,user,host,_,service=setup
    content=service.issue_file(db,user,host,'198.51.100.10').decode('utf-16')
    assert 'full address:s:rdp.example.test:13389\r\n' in content
    assert 'username:s:rdp-user#win-1\r\n' in content
    assert 'authentication level:i:1' in content and 'enablecredsspsupport:i:1' in content
    for secret in ['windows-test-password','platform-test-password','win.internal','administrator','gatewayaccesstoken','password 51:']:
        assert secret not in content

def test_inactive_connection_and_failure_limits(setup):
    db,user,host,_,service=setup
    for _ in range(8):assert service._admit('198.51.100.10')
    assert not service._admit('198.51.100.10')
    service._ips['198.51.100.10']['active']=0;service._active=0
    for _ in range(10):
        with pytest.raises(HTTPException):service.authorize(db,12345,'rdp-user#win-1','wrong')
    assert not service._admit('198.51.100.10')


def test_nla_requires_web_password_login_and_returns_only_identity_specific_verifier(setup):
    db,user,host,grant,service=setup
    name=user.username+'#'+host.name
    with pytest.raises(HTTPException):service.authorize(db,12345,name,'','ntlm')
    assert not authenticate_user(db,user.username,'wrong')
    assert ntlm_verifier(user) is None
    assert authenticate_user(db,user.username,'platform-test-password')==user
    value=service.authorize(db,12345,name,'','ntlm','DOMAIN')
    from passlib.hash import nthash
    import hmac
    expected=hmac.new(bytes.fromhex(nthash.hash('platform-test-password')),(name.upper()+'DOMAIN').encode('utf-16-le'),'md5').hexdigest()
    assert value=={'ntlm_v2':expected}
    assert nthash.hash('platform-test-password') not in user.rdp_ntlm_encrypted
    assert not service._sessions[12345].authorized
    with pytest.raises(HTTPException):service.authorize(db,12345,name,'wrong')
    assert login(setup)['username']=='administrator'


@pytest.mark.parametrize('change',['password','grant','user','host','corrupt_verifier'])
def test_nla_verifier_respects_password_and_access_revocation(setup,change):
    db,user,host,grant,service=setup
    authenticate_user(db,user.username,'platform-test-password')
    if change=='password':user.password_hash=get_password_hash('new-password')
    if change=='grant':grant.is_active=False
    if change=='user':user.is_active=False
    if change=='host':host.is_active=False
    if change=='corrupt_verifier':user.rdp_ntlm_encrypted='corrupt'
    db.commit()
    with pytest.raises(HTTPException):service.authorize(db,12345,user.username+'#'+host.name,'','ntlm')


def test_rdp_negotiation_is_length_bounded_and_preserved():
    class Socket:
        def __init__(self, data): self.data=data
        def recv(self, size):
            # Force fragmented reads, as on a real TCP connection.
            part,self.data=self.data[:min(size,2)],self.data[min(size,2):]
            return part
    packet=bytes.fromhex('030000130ee000000000000100080001000000')
    assert RDPGatewayService._tpkt(Socket(packet))==packet
    for data in [b'\x03\x00\xff\xff',b'\x03\x00\x00\x04',b'\x03\x00\x00\x13\x0e',b'GET /']:
        with pytest.raises(OSError):RDPGatewayService._tpkt(Socket(data))


def test_tls_control_records_do_not_block_the_opposite_rdp_direction(setup,monkeypatch):
    import ssl
    from types import SimpleNamespace
    request=bytes.fromhex('030000130ee000000000000100080003000000')
    response=bytes.fromhex('030000130ed000001234000200080002000000')
    class Socket:
        def __init__(self,negotiation,events):
            self.negotiation=negotiation;self.events=iter(events);self.sent=[]
        def recv(self,size):
            if self.negotiation:
                data,self.negotiation=self.negotiation[:size],self.negotiation[size:]
                return data
            data=next(self.events)
            if isinstance(data,Exception):raise data
            return data
        def sendall(self,data):self.sent.append(data)
        def settimeout(self,value):pass
        def pending(self):return 0
        def getsockname(self):return ('127.0.0.1',23456)
        def close(self):pass
    client=Socket(request,[ssl.SSLWantReadError(),'client-rdp'.encode()])
    upstream=Socket(response,[b'server-rdp',b''])
    db,user,host,grant,service=setup
    service._sessions.clear()
    service._tls_server=service._tls_proxy=SimpleNamespace(wrap_socket=lambda sock,**kw:sock)
    monkeypatch.setattr(module.socket,'create_connection',lambda *a,**kw:upstream)
    monkeypatch.setattr(module.select,'select',lambda *a:([client,upstream],[],[]))
    assert service._admit('198.51.100.10')
    service._relay(client,'198.51.100.10',50000)
    assert client.sent==[response,b'server-rdp']
    assert upstream.sent==[request,b'client-rdp']
    assert service._active==0 and not service._sessions

def test_internal_callback_cannot_be_called_from_public_api(setup):
    db,user,host,_,service=setup
    app.dependency_overrides[get_db]=lambda:db
    try:
        client=TestClient(app)
        result=client.post('/api/managed-hosts/gateway/rdp/authorize',json={'connection_port':12345,'username':'rdp-user#win-1','password':'platform-test-password'},headers={'X-Rdp-Internal-Secret':service.internal_secret})
        assert result.status_code==403
    finally:app.dependency_overrides.clear()

def request(peer,headers=(),scheme='http'):
    return Request({'type':'http','scheme':scheme,'method':'POST','path':'/','query_string':b'','server':('portal.test',443),'client':(peer,1234),'headers':headers})

def test_real_source_and_https_are_only_accepted_from_trusted_proxy(monkeypatch):
    settings=get_settings();monkeypatch.setattr(settings,'rdp_gateway_trusted_proxies','172.25.0.2/32')
    headers=[(b'x-forwarded-for',b'198.51.100.10'),(b'x-forwarded-proto',b'https')]
    assert rdp_client_ip(request('172.25.0.2',headers))=='198.51.100.10'
    require_secure_rdp_download(request('172.25.0.2',headers))
    assert rdp_client_ip(request('203.0.113.1',headers))=='203.0.113.1'
    with pytest.raises(HTTPException):require_secure_rdp_download(request('203.0.113.1',headers))
