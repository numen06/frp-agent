"""Live TLS/WebSocket -> direct RFB and optional SSH acceptance, on disposable container data only.

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
import re
from pathlib import Path
import secrets
import select
import socket
import ssl
import struct
import subprocess
import sys
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
        self.key_events = []
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
                    self.key_events.append(struct.unpack('!B2xI',read(sock,7)))
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
            forwarded = set()
            def check_auth_password(self, username, password):
                return paramiko.AUTH_SUCCESSFUL if username == 'fixture' and password == fixture.ssh_password else paramiko.AUTH_FAILED
            def get_allowed_auths(self, username): return 'password'
            def check_channel_request(self, kind, chanid):
                return paramiko.OPEN_SUCCEEDED if kind == 'session' else paramiko.OPEN_FAILED_ADMINISTRATIVELY_PROHIBITED
            def check_channel_exec_request(self, channel, command):
                def reply():
                    time.sleep(.05)
                    channel.sendall(b'Darwin | Kernel fixture | arm64\n')
                    channel.send_exit_status(0)
                    channel.close()
                background(reply)
                return True
            def check_channel_direct_tcpip_request(self, chanid, origin, destination):
                self.forwarded.add(chanid)
                return paramiko.OPEN_SUCCEEDED if destination == ('127.0.0.1',fixture.rfb.getsockname()[1]) else paramiko.OPEN_FAILED_ADMINISTRATIVELY_PROHIBITED
        transport = paramiko.Transport(sock)
        transport.add_server_key(self.key)
        try:
            server = Server()
            transport.start_server(server=server)
            while transport.is_active():
                channel = transport.accept(1)
                if channel is not None and channel.get_id() in server.forwarded: background(self.forward,channel)
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


def check_native_gateway(port, key, password, fixture, revoke):
    from app.services.vnc_service import challenge_response

    def client_for(username):
        client = paramiko.SSHClient()
        client.get_host_keys().add(f'[127.0.0.1]:{port}', key.get_name(), key)
        try:
            client.connect('127.0.0.1', port=port, username=f'{username}#test-vnc',
                           password=password, allow_agent=False, look_for_keys=False, timeout=5)
        except BaseException:
            client.close()
            raise
        return client

    def open_forward(transport, destination):
        return transport.open_channel('direct-tcpip', destination, ('127.0.0.1', 0), timeout=5)

    try:
        client_for('vnc-viewer')
    except paramiko.AuthenticationException:
        pass
    else:
        raise AssertionError('An ungranted account authenticated to native VNC')

    def screen_session(client):
        transport = client.get_transport()
        setup = transport.open_session(timeout=5)
        setup.settimeout(5)
        setup.exec_command('vnc')
        code = re.search(rb'[0-9a-f]{8}', setup.makefile('rb').readline())[0].decode()
        try:
            open_forward(transport, ('127.0.0.1', 5900))
        except paramiko.ChannelException:
            pass
        else:
            raise AssertionError('Arbitrary SSH forwarding was accepted')
        vnc = open_forward(transport, ('frp-vnc', 5900))
        vnc.settimeout(12)
        assert read(vnc, 12) == b'RFB 003.008\n'
        vnc.sendall(b'RFB 003.003\n')  # macOS Screen Sharing negotiates this version.
        assert read(vnc, 4) == b'\0\0\0\x02'
        return code, vnc, read(vnc, 16)

    before = fixture.authenticated
    with client_for('vnc-operator') as client:
        code, vnc, challenge = screen_session(client)
        invalid = '00000000' if code != '00000000' else 'ffffffff'
        vnc.sendall(challenge_response(invalid, challenge))
        assert read(vnc, 4) == b'\0\0\0\x01'
    assert fixture.authenticated == before

    with client_for('vnc-operator') as client:
        code, vnc, challenge = screen_session(client)
        vnc.sendall(challenge_response(code, challenge))
        assert read(vnc, 4) == b'\0'*4
        vnc.sendall(b'\x01')
        assert read(vnc, len(fixture.initial)) == fixture.initial
        vnc.sendall(b'\x03\0'+struct.pack('!HHHH',0,0,16,16))
        assert read(vnc, len(fixture.frame)) == fixture.frame
        revoke()
        assert vnc.recv(1) == b'', 'Revoked native session remained connected'
    print('Native SSH gateway: platform login, local VNC code, desktop frame and revocation passed',flush=True)


def check_apple_gateway(port, client, host, password, fixture, revoke):
    """Drive the RSA-SRP proof and RFB records through the production listener."""
    import hashlib
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
    from cryptography.hazmat.primitives.serialization import load_der_public_key
    from cryptography.hazmat.primitives.asymmetric import padding
    from app.services.vnc_apple_protocol import GENERATOR, GROUP, MODULUS, digest, field, number

    ticket_url = f"/api/managed-hosts/{host['id']}/vnc-ticket"
    assert client.post(ticket_url, auth=None).status_code == 401
    assert client.post(ticket_url, auth=('vnc-viewer', password)).status_code == 403
    response = client.post(ticket_url, auth=('vnc-operator', password))
    assert response.headers['cache-control'] == 'no-store'
    ticket = response.raise_for_status().json()

    def packet(sock):
        return read(sock, int.from_bytes(read(sock, 4), 'big'))

    def envelope(payload, op):
        return field(b'\x01\x00RSA1' + number(op, 2) + field(payload, 2), 4)

    def handshake(sock, credential, valid):
        version = read(sock, 12)
        assert version == b'RFB 003.889\n'
        sock.sendall(version)
        assert read(sock, 3) == b'\x02\x21\x24'
        sock.sendall(b'\x21' + envelope(b'', 0))
        reply = packet(sock)
        der_size = int.from_bytes(reply[2:6], 'big')
        key = load_der_public_key(reply[6:6 + der_size])
        username = field(ticket['username'].encode(), 4) + bytes(3)
        sock.sendall(envelope(key.encrypt(field(username, 4), padding.PKCS1v15()), 2))
        challenge = packet(sock)
        assert challenge[13:525] == GROUP
        salt = challenge[529:561]
        server_public = challenge[563:1075]
        iterations = int.from_bytes(challenge[1075:1083], 'big')
        options = challenge[1085:]
        exponent = int.from_bytes(digest(salt + digest(
            b':' + hashlib.pbkdf2_hmac('sha512', credential.encode(), salt, iterations, 128)
        )), 'big')
        a = secrets.randbits(512)
        public = number(pow(GENERATOR, a, MODULUS), 512)
        g = number(GENERATOR, 512)
        k = int.from_bytes(digest(GROUP + g), 'big')
        u = int.from_bytes(digest(public + server_public), 'big')
        shared = pow((int.from_bytes(server_public, 'big') - k * pow(GENERATOR, exponent, MODULUS)) % MODULUS,
                     a + u * exponent, MODULUS)
        key = digest(number(shared, 512))
        proof = digest(bytes(a ^ b for a, b in zip(digest(GROUP), digest(g))) + digest(b'')
                       + salt + public + server_public + key)
        inner = field(public, 2) + field(proof, 1) + field(options, 2) + field(secrets.token_bytes(16), 1)
        sock.sendall(envelope(bytes(2) + field(inner, 2), 2))
        if not valid:
            assert sock.recv(1) == b'', 'Rejected credential received data'
            return
        server_proof = packet(sock)
        assert server_proof[11:75] == digest(public + proof + key)
        assert read(sock, 4) == bytes(4)
        sock.sendall(b'\xc1')
        initial = read(sock, 24)
        assert initial[:20] == fixture.initial[:20]
        assert read(sock, int.from_bytes(initial[20:24], 'big')) == bytes(22) + fixture.initial[24:]
        rekey = read(sock, 52)
        wrap = Cipher(algorithms.AES(hashlib.sha256(key).digest()[:16]), modes.ECB()).decryptor()
        material = wrap.update(rekey[20:]) + wrap.finalize()
        cipher = Cipher(algorithms.AES(material[:16]), modes.CBC(material[16:]))
        return cipher.encryptor(), cipher.decryptor()

    def connection():
        return socket.create_connection(('127.0.0.1', port), timeout=12)

    before = fixture.authenticated
    with connection() as sock:
        handshake(sock, 'incorrect', valid=False)
    assert fixture.authenticated == before
    with connection() as sock:
        encrypt, decrypt = handshake(sock, ticket['password'], valid=True)
        request = field(b'\x03\0' + struct.pack('!HHHH', 0, 0, 16, 16), 2)
        request += bytes((-(len(request) + 20)) % 16)
        request += hashlib.sha1(bytes(4) + request).digest()
        sock.sendall(field(encrypt.update(request), 2))
        plain = decrypt.update(read(sock, int.from_bytes(read(sock, 2), 'big')))
        assert plain[-20:] == hashlib.sha1(bytes(4) + plain[:-20]).digest()
        assert plain[2:2 + int.from_bytes(plain[:2], 'big')] == fixture.frame
        revoke()
        assert sock.recv(1) == b'', 'Revoked native VNC remained connected'
    with connection() as sock:
        handshake(sock, ticket['password'], valid=False)
    assert fixture.authenticated == before + 1
    print('Apple VNC gateway: encrypted frame, ACL, wrong password, revocation and replay passed', flush=True)
    return ticket['password']


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
        ssh_socket = listen(); ssh_port = ssh_socket.getsockname()[1]; ssh_socket.close()
        apple_socket = listen(); apple_port = apple_socket.getsockname()[1]; apple_socket.close()
        fixture.key.write_private_key_file(str(folder/'gateway_key'))
        base = f'https://127.0.0.1:{port}'
        log = (folder/'server.log').open('w')
        server = subprocess.Popen([sys.executable,'-m','uvicorn','app.main:app','--host','127.0.0.1','--port',str(port),
                                   '--ssl-keyfile',str(folder/'key.pem'),'--ssl-certfile',str(folder/'cert.pem')],stdout=log,stderr=log,
                                  env={**os.environ, 'SSH_GATEWAY_ENABLED':'true', 'SSH_GATEWAY_HOST':'127.0.0.1',
                                       'SSH_GATEWAY_PORT':str(ssh_port), 'SSH_GATEWAY_HOST_KEY_PATH':str(folder/'gateway_key'),
                                       'VNC_GATEWAY_ENABLED':'true', 'VNC_GATEWAY_HOST':'127.0.0.1',
                                       'VNC_GATEWAY_PORT':str(apple_port), 'VNC_GATEWAY_KEY_PATH':str(folder/'apple.pem')})
        try:
            client = httpx.Client(base_url=base,auth=(os.environ['AUTH_USERNAME'],os.environ['AUTH_PASSWORD']),
                                  verify=str(folder/'cert.pem'),timeout=15,trust_env=False)
            for _ in range(120):
                try:
                    if client.get('/api/public/version').status_code == 200: break
                except httpx.HTTPError: pass
                if server.poll() is not None:
                    raise RuntimeError((folder/'server.log').read_text())
                time.sleep(.25)
            else: raise RuntimeError('HTTPS application readiness timeout')
            if os.environ.get('EXPECTED_APP_VERSION'):
                assert client.get('/api/public/version').json()['version'] == os.environ['EXPECTED_APP_VERSION']
            def api(method,path,**kwargs):
                response = client.request(method,'/api/'+path,**kwargs)
                if response.status_code >= 400: raise RuntimeError(f'{method} {path}: HTTP {response.status_code}: {response.text[:200]}')
                return response.json() if response.content else None
            assert client.get('/api/managed-hosts',auth=None).status_code == 401
            machine = api('POST','host-machines',json=dict(name='Disposable Mac'))
            ssh_cred = api('POST','ssh-credentials',json=dict(name='test-ssh',username='fixture',auth_type='password',password=fixture.ssh_password))
            ssh_host = api('POST','managed-hosts',json=dict(machine_id=machine['id'],name='test-ssh',host_type='ssh',address='127.0.0.1',port=fixture.ssh.getsockname()[1],credential_id=ssh_cred['id'],host_key_fingerprint=format_host_key_fingerprint(fixture.key)))
            vnc_cred = api('POST','ssh-credentials',json=dict(name='test-vnc',username='vnc',auth_type='password',password=fixture.password))
            host = api('POST','managed-hosts',json=dict(machine_id=machine['id'],name='test-vnc',host_type='vnc',address='127.0.0.1',port=fixture.rfb.getsockname()[1],credential_id=vnc_cred['id']))
            assert host['vnc_ssh_host_id'] is None
            assert api('GET',f"host-machines/{machine['id']}")['service_count']==2
            grant = api('POST','managed-hosts/access/grants',json=dict(host_id=host['id'],subject_type='user',subject_id=operator_id,can_connect=True))
            result = api('POST',f"managed-hosts/{host['id']}/test")
            assert result['success'], result
            print('HTTPS startup, migration, one machine with separate services and direct VNC password test: passed',flush=True)
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
                print('Real WSS -> direct VNC framebuffer, Origin/query rejection, permissions and live grant revocation: passed',flush=True)
            asyncio.run(live())
            api('PUT',f"managed-hosts/access/grants/{grant['id']}",json=dict(is_active=True))
            check_native_gateway(ssh_port, fixture.key, operator_password, fixture,
                lambda: api('PUT',f"managed-hosts/access/grants/{grant['id']}",json=dict(is_active=False)))
            api('PUT',f"managed-hosts/access/grants/{grant['id']}",json=dict(is_active=True))
            ticket_password = check_apple_gateway(apple_port, client, host, operator_password, fixture,
                lambda: api('PUT',f"managed-hosts/access/grants/{grant['id']}",json=dict(is_active=False)))
            logs = api('GET','managed-hosts/audit/logs',params=dict(page=1,page_size=100))
            rows = logs['items'] if isinstance(logs,dict) else logs
            assert {'vnc_connected','vnc_session'}.issubset({x['action'] for x in rows})
            assert fixture.password not in json.dumps(rows) and fixture.ssh_password not in json.dumps(rows)
            assert ticket_password not in json.dumps(rows)
            api('PUT',f"managed-hosts/{host['id']}",json=dict(vnc_ssh_host_id=ssh_host['id']))
            assert api('POST',f"managed-hosts/{host['id']}/test")['success']
            api('PUT',f"managed-hosts/{ssh_host['id']}",json=dict(host_key_fingerprint='SHA256:wrong'))
            denied = client.post(f"/api/managed-hosts/{host['id']}/test")
            assert denied.status_code == 502 and '指纹不匹配' in denied.text
            api('PUT',f"managed-hosts/{ssh_host['id']}",json=dict(host_key_fingerprint=format_host_key_fingerprint(fixture.key)))
            api('PUT',f"ssh-credentials/{vnc_cred['id']}",json=dict(password='badpass'))
            denied = client.post(f"/api/managed-hosts/{host['id']}/test")
            assert denied.status_code == 502 and '密码认证失败' in denied.text
            print('Audit records without target passwords; wrong SSH fingerprint and wrong VNC password block connection: passed',flush=True)
            print(json.dumps(dict(status='passed',transport='HTTPS/WSS + Apple RSA-SRP + native SSH gateway + direct VNC + optional SSH',vnc_fixture_authenticated=fixture.authenticated,frame_requests=fixture.frame_requests,real_mac=False)),flush=True)
        finally:
            server.terminate()
            try: server.wait(timeout=10)
            except subprocess.TimeoutExpired: server.kill();server.wait()
            log.close(); fixture.ssh.close(); fixture.rfb.close()


if __name__ == '__main__': main()
