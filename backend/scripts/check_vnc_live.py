"""Live TLS/WebSocket -> real SSH -> RFB acceptance, on disposable container data only.

Run inside an isolated test container, with PYTHONPATH=/app/backend. Never point
DATABASE_URL at an existing deployment. No host ports or real Mac are required.
"""
import asyncio
import base64
import datetime
from contextlib import suppress
import ipaddress
import json
import os
from pathlib import Path
import secrets
import select
import socket
import ssl
import struct
import subprocess
import tempfile
import threading
import time

import httpx
import paramiko
import websockets
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID


def read(sock, count):
    data = b''
    while len(data) < count:
        chunk = sock.recv(count-len(data))
        if not chunk:
            raise EOFError()
        data += chunk
    return data


def listen():
    sock = socket.socket()
    sock.bind(('127.0.0.1', 0))
    sock.listen(16)
    return sock


def background(fn, *args):
    threading.Thread(target=fn, args=args, daemon=True).start()


class DesktopFixture:
    """A password-protected RFB fixture behind a real pinned SSH server."""
    def __init__(self):
        self.key = paramiko.RSAKey.generate(2048)
        self.password = secrets.token_hex(4)
        self.ssh_password = secrets.token_hex(16)
        self.rfb, self.ssh = listen(), listen()
        self.initial = (struct.pack('!HH', 16, 16) + bytes([32,24,0,1])
                        + struct.pack('!HHH',255,255,255) + bytes([16,8,0,0,0,0])
                        + struct.pack('!I',12) + b'Test Desktop')
        self.frame = b'\0\0\0\1' + struct.pack('!HHHHi',0,0,16,16,0) + bytes([64,128,192,0])*256
        self.authenticated = 0
        self.frame_requests = 0
        background(self.accept, self.rfb, self.desktop)
        background(self.accept, self.ssh, self.transport)

    def accept(self, listener, fn):
        while True:
            try:
                sock, _ = listener.accept()
                sock.settimeout(10)
                background(fn, sock)
            except OSError:
                return

    def desktop(self, sock):
        from app.services.vnc_service import challenge_response
        try:
            sock.sendall(b'RFB 003.889\n')
            assert read(sock,12) == b'RFB 003.008\n'
            sock.sendall(b'\x01\x02')
            assert read(sock,1) == b'\x02'
            challenge = secrets.token_bytes(16)
            sock.sendall(challenge)
            if read(sock,16) != challenge_response(self.password,challenge):
                sock.sendall(b'\0\0\0\1'); return
            self.authenticated += 1
            sock.sendall(b'\0'*4)
            assert read(sock,1) == b'\x01'
            sock.sendall(self.initial)
            while True:
                kind = read(sock,1)[0]
                if kind == 0:
                    read(sock,19)
                elif kind == 2:
                    count = int.from_bytes(read(sock,3)[1:], 'big'); read(sock,4*count)
                elif kind == 3:
                    read(sock,9); self.frame_requests += 1; sock.sendall(self.frame)
                elif kind == 4:
                    read(sock,7)
                elif kind == 5:
                    read(sock,5)
                else:
                    raise ValueError('Unexpected fixture input')
        except (EOFError, OSError):
            pass
        finally:
            sock.close()

    def transport(self, sock):
        fixture = self
        class Server(paramiko.ServerInterface):
            def check_auth_password(self, username, password):
                return paramiko.AUTH_SUCCESSFUL if username == 'fixture' and password == fixture.ssh_password else paramiko.AUTH_FAILED
            def get_allowed_auths(self, username): return 'password'
            def check_channel_direct_tcpip_request(self, chanid, origin, destination):
                return paramiko.OPEN_SUCCEEDED if destination == ('127.0.0.1',fixture.rfb.getsockname()[1]) else paramiko.OPEN_FAILED_ADMINISTRATIVELY_PROHIBITED
        transport = paramiko.Transport(sock)
        transport.add_server_key(self.key)
        try:
            transport.start_server(server=Server())
            while transport.is_active():
                channel = transport.accept(1)
                if channel is not None: background(self.forward,channel)
        except (EOFError,OSError,paramiko.SSHException):
            pass
        finally:
            transport.close()

    def forward(self, channel):
        upstream = socket.create_connection(self.rfb.getsockname(),timeout=10)
        try:
            while True:
                ready, _, _ = select.select([channel,upstream],[],[],1)
                for source in ready:
                    data = source.recv(32768)
                    if not data: return
                    (upstream if source is channel else channel).sendall(data)
        except (OSError,EOFError):
            pass
        finally:
            with suppress(EOFError, OSError): channel.close()
            upstream.close()


def certificate(folder):
    key = rsa.generate_private_key(public_exponent=65537,key_size=2048)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME,'localhost')])
    now = datetime.datetime.now(datetime.timezone.utc)
    cert = (x509.CertificateBuilder().subject_name(name).issuer_name(name).public_key(key.public_key())
            .serial_number(x509.random_serial_number()).not_valid_before(now-datetime.timedelta(minutes=1))
            .not_valid_after(now+datetime.timedelta(days=1))
            .add_extension(x509.SubjectAlternativeName([x509.DNSName('localhost'),x509.IPAddress(ipaddress.ip_address('127.0.0.1'))]),False)
            .sign(key,hashes.SHA256()))
    (folder/'cert.pem').write_bytes(cert.public_bytes(serialization.Encoding.PEM))
    (folder/'key.pem').write_bytes(key.private_bytes(serialization.Encoding.PEM,serialization.PrivateFormat.PKCS8,serialization.NoEncryption()))


def main():
    if os.environ.get('VNC_DISPOSABLE_TEST') != '1':
        raise RuntimeError('Requires an explicitly disposable test environment')
    from app.auth import get_password_hash
    from app.database import init_db, SessionLocal
    from app.models.user import User
    from app.services.ssh_client import format_host_key_fingerprint
    init_db()
    fixture = DesktopFixture()
    operator_password = secrets.token_hex(16)
    with SessionLocal() as db:
        user = User(username='vnc-operator',password_hash=get_password_hash(operator_password),role='user',is_active=True)
        viewer = User(username='vnc-viewer',password_hash=get_password_hash(operator_password),role='user',is_active=True)
        db.add_all([user,viewer]); db.commit(); operator_id = user.id
    with tempfile.TemporaryDirectory(prefix='vnc-live-') as temporary:
        folder = Path(temporary); certificate(folder)
        port_socket = listen(); port = port_socket.getsockname()[1]; port_socket.close()
        base = f'https://127.0.0.1:{port}'
        log = (folder/'server.log').open('w')
        server = subprocess.Popen(['python','-m','uvicorn','app.main:app','--host','127.0.0.1','--port',str(port),
                                   '--ssl-keyfile',str(folder/'key.pem'),'--ssl-certfile',str(folder/'cert.pem')],stdout=log,stderr=log)
        try:
            client = httpx.Client(base_url=base,auth=(os.environ['AUTH_USERNAME'],os.environ['AUTH_PASSWORD']),
                                  verify=str(folder/'cert.pem'),timeout=15,trust_env=False)
            for _ in range(120):
                try:
                    if client.get('/api/public/version').status_code == 200: break
                except httpx.HTTPError: pass
                if server.poll() is not None: raise RuntimeError('Application exited during startup')
                time.sleep(.25)
            else: raise RuntimeError('HTTPS application readiness timeout')
            if os.environ.get('EXPECTED_APP_VERSION'):
                assert client.get('/api/public/version').json()['version'] == os.environ['EXPECTED_APP_VERSION']
            def api(method,path,**kwargs):
                response = client.request(method,'/api/'+path,**kwargs)
                if response.status_code >= 400: raise RuntimeError(f'{method} {path}: HTTP {response.status_code}: {response.text[:200]}')
                return response.json() if response.content else None
            assert client.get('/api/managed-hosts',auth=None).status_code == 401
            ssh_cred = api('POST','ssh-credentials',json=dict(name='test-ssh',username='fixture',auth_type='password',password=fixture.ssh_password))
            ssh_host = api('POST','managed-hosts',json=dict(name='test-ssh',host_type='ssh',address='127.0.0.1',port=fixture.ssh.getsockname()[1],credential_id=ssh_cred['id'],host_key_fingerprint=format_host_key_fingerprint(fixture.key)))
            vnc_cred = api('POST','ssh-credentials',json=dict(name='test-vnc',username='vnc',auth_type='password',password=fixture.password))
            host = api('POST','managed-hosts',json=dict(name='test-vnc',host_type='vnc',address='127.0.0.1',port=fixture.rfb.getsockname()[1],vnc_ssh_host_id=ssh_host['id'],credential_id=vnc_cred['id']))
            grant = api('POST','managed-hosts/access/grants',json=dict(host_id=host['id'],subject_type='user',subject_id=operator_id,can_connect=True))
            result = api('POST',f"managed-hosts/{host['id']}/test")
            assert result['success'], result
            print('HTTPS startup, migration, credentials, host CRUD and real SSH/VNC password test: passed',flush=True)
            tls = ssl.create_default_context(cafile=str(folder/'cert.pem'))
            uri = f"wss://127.0.0.1:{port}/api/managed-hosts/{host['id']}/vnc"
            async def live():
                for bad_uri, origin in [(uri,'https://evil.invalid'),(uri+'?token=forbidden',base)]:
                    try:
                        async with websockets.connect(bad_uri,ssl=tls,origin=origin): pass
                    except Exception as exc:
                        assert getattr(exc,'status_code',None)==403 or getattr(getattr(exc,'response',None),'status_code',None)==403
                    else: raise AssertionError('Unsafe WebSocket was accepted')
                def auth(username):
                    return json.dumps(dict(type='auth',authorization='Basic '+base64.b64encode(f'{username}:{operator_password}'.encode()).decode()))
                async with websockets.connect(uri,ssl=tls,origin=base) as ws:
                    await ws.send(auth('vnc-viewer'))
                    assert json.loads(await ws.recv())['type']=='error'
                async with websockets.connect(uri,ssl=tls,origin=base) as ws:
                    await ws.send(auth('vnc-operator'))
                    assert json.loads(await ws.recv()) == {'type':'ready'}
                    assert await ws.recv() == b'RFB 003.008\n'
                    await ws.send(b'RFB 003.008\n'); assert await ws.recv()==b'\x01\x01'
                    await ws.send(b'\x01'); assert await ws.recv()==b'\0'*4
                    await ws.send(b'\x01'); assert await ws.recv()==fixture.initial
                    await ws.send(b'\x03\0'+struct.pack('!HHHH',0,0,16,16))
                    data = b''
                    while len(data)<len(fixture.frame): data += await asyncio.wait_for(ws.recv(),10)
                    assert data == fixture.frame
                    # Revoke through the same real HTTP API while the desktop is active.
                    await asyncio.to_thread(api,'PUT',f"managed-hosts/access/grants/{grant['id']}",json=dict(is_active=False))
                    try: await asyncio.wait_for(ws.recv(),12)
                    except websockets.exceptions.ConnectionClosed: pass
                    else: raise AssertionError('Revoked session remained connected')
                print('Real WSS -> pinned SSH -> VNC framebuffer, Origin/query rejection, permissions and live grant revocation: passed',flush=True)
            asyncio.run(live())
            logs = api('GET','managed-hosts/audit/logs',params=dict(page=1,page_size=100))
            rows = logs['items'] if isinstance(logs,dict) else logs
            assert {'vnc_connected','vnc_session'}.issubset({x['action'] for x in rows})
            assert fixture.password not in json.dumps(rows) and fixture.ssh_password not in json.dumps(rows)
            api('PUT',f"managed-hosts/{ssh_host['id']}",json=dict(host_key_fingerprint='SHA256:wrong'))
            denied = client.post(f"/api/managed-hosts/{host['id']}/test")
            assert denied.status_code == 502 and '指纹不匹配' in denied.text
            api('PUT',f"managed-hosts/{ssh_host['id']}",json=dict(host_key_fingerprint=format_host_key_fingerprint(fixture.key)))
            api('PUT',f"ssh-credentials/{vnc_cred['id']}",json=dict(password='badpass'))
            denied = client.post(f"/api/managed-hosts/{host['id']}/test")
            assert denied.status_code == 502 and '密码认证失败' in denied.text
            print('Audit records without target passwords; wrong SSH fingerprint and wrong VNC password block connection: passed',flush=True)
            print(json.dumps(dict(status='passed',transport='HTTPS/WSS + SSH',vnc_fixture_authenticated=fixture.authenticated,frame_requests=fixture.frame_requests,real_mac=False)),flush=True)
        finally:
            server.terminate()
            try: server.wait(timeout=10)
            except subprocess.TimeoutExpired: server.kill();server.wait()
            log.close(); fixture.ssh.close(); fixture.rfb.close()


if __name__ == '__main__': main()
