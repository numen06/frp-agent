"""Isolated Linux acceptance using an existing image; never accesses production.

Run from the repository root:
  python backend/scripts/check_runtime_container.py [frp-agent:integration-check]
"""
import datetime
import json
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import httpx
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID

ROOT = Path(__file__).resolve().parents[2]


def docker(*args, input=None):
    result = subprocess.run(['docker', *args], input=input, capture_output=True, check=True)
    return (result.stdout + result.stderr if args[0] == 'logs' else result.stdout).decode().strip()


def main():
    image = sys.argv[1] if len(sys.argv) > 1 else 'frp-agent:integration-check'
    name = 'frp-runtime-acceptance-' + str(int(time.time()))
    with tempfile.TemporaryDirectory(prefix='frp-runtime-') as folder:
        data = Path(folder)
        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        subject = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, 'localhost')])
        now = datetime.datetime.now(datetime.timezone.utc)
        cert = (x509.CertificateBuilder().subject_name(subject).issuer_name(subject).public_key(key.public_key())
                .serial_number(x509.random_serial_number()).not_valid_before(now-datetime.timedelta(minutes=1))
                .not_valid_after(now+datetime.timedelta(days=1)).add_extension(x509.SubjectAlternativeName([x509.DNSName('localhost')]), False)
                .sign(key, hashes.SHA256()))
        (data/'cert.pem').write_bytes(cert.public_bytes(serialization.Encoding.PEM))
        (data/'key.pem').write_bytes(key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()))
        try:
            docker('run', '-d', '--name', name, '--memory', '384m', '--cpus', '.5', '--pids-limit', '128',
                   '-p', '127.0.0.1::8000', '-p', '127.0.0.1::13389',
                   '-v', str(ROOT/'backend')+':/app/backend:ro', '-v', str(ROOT/'dist')+':/app/dist:ro',
                   '-v', folder+':/app/data', '-e', 'AUTH_USERNAME=runtime-admin', '-e', 'AUTH_PASSWORD=isolated-runtime-test',
                   '-e', 'SSH_CREDENTIAL_SECRET=isolated-runtime-secret', '-e', 'SSH_GATEWAY_ENABLED=false',
                   '-e', 'DOCKER_GATEWAY_ENABLED=false', '-e', 'RDP_GATEWAY_ENABLED=true',
                   '-e', 'RDP_GATEWAY_PUBLIC_ADDRESS=localhost:13389', '-e', 'RDP_GATEWAY_TLS_CERT_PATH=/app/data/cert.pem',
                   '-e', 'RDP_GATEWAY_TLS_KEY_PATH=/app/data/key.pem', image)
            bindings = json.loads(docker('inspect', name))[0]['NetworkSettings']['Ports']
            http_port = int(bindings['8000/tcp'][0]['HostPort']); rdp_port = int(bindings['13389/tcp'][0]['HostPort'])
            with httpx.Client(base_url=f'http://127.0.0.1:{http_port}', auth=('runtime-admin', 'isolated-runtime-test'), timeout=5, trust_env=False) as client:
                for _ in range(90):
                    try:
                        response = client.get('/api/system/overview')
                        if response.status_code == 200 and response.json()['latest']['rdp']['running']:
                            break
                    except (httpx.HTTPError, TypeError):
                        pass
                    time.sleep(.25)
                else:
                    raise AssertionError('Startup failed: '+docker('logs', name)[:4000])
                first = response.json()
                assert first['latest']['scope'] == 'container'
                assert first['latest']['app']['cpu_cores'] == .5
                assert first['latest']['app']['memory_limit_bytes'] == 384 * 1024**2
                assert first['latest']['app']['memory_used_bytes'] > 0
                assert client.get('/api/system/overview', auth=None).status_code == 401
                print('Linux cgroup limits, process group memory, admin authentication, native RDP startup: passed', flush=True)
                # Real bad TLS handshakes through the Python + native FreeRDP chain.
                request = bytes.fromhex('030000130ee000000000000100080003000000')
                for _ in range(10):
                    with socket.create_connection(('127.0.0.1', rdp_port), timeout=4) as sock:
                        sock.settimeout(4); sock.sendall(request)
                        assert sock.recv(19).startswith(b'\x03\x00')
                        sock.sendall(b'not-a-valid-TLS-handshake\r\n')
                    time.sleep(.1)
                time.sleep(.5)
                with socket.create_connection(('127.0.0.1', rdp_port), timeout=3) as sock:
                    sock.settimeout(3)
                    try:
                        sock.sendall(request); assert sock.recv(19) == b''
                    except ConnectionResetError:
                        pass
                print('Ten malformed client handshakes temporarily block new connections: passed', flush=True)
                normal_client = '''import socket,ssl
s=socket.create_connection(('127.0.0.1',13389),timeout=4)
s.sendall(bytes.fromhex('030000130ee000000000000100080003000000'))
assert s.recv(19).startswith(b'\\x03\\x00')
with ssl._create_unverified_context().wrap_socket(s,server_hostname='localhost') as tls:
 print(tls.version())
'''
                assert 'TLS' in docker('exec', '-i', name, 'python', '-', input=normal_client.encode())
                print('A different source still completes a real TLS handshake: passed', flush=True)
                # Wait for the actual in-process scheduled sampler, not an imported test singleton.
                for _ in range(90):
                    current = client.get('/api/system/overview').json()
                    if current['latest']['rdp']['counts'].get('handshake_failures', 0) >= 10:
                        break
                    time.sleep(1)
                else:
                    raise AssertionError('Scheduled RDP counters did not persist')
                assert current['latest']['rdp']['counts']['rejected'] >= 1
                assert current['latest']['rdp']['counts']['native_error_lines'] > 0
                assert current['latest']['rdp']['blocked_sources'] == 1
                assert current['latest']['app']['cpu_percent'] is not None
                logs = docker('logs', name)
                assert '[ERROR][com.freerdp' not in logs
                assert 'RDP 网关采样周期汇总' in logs
                assert 'was missed' not in logs
                print('Scheduled resource/RDP persistence, CPU second sample and aggregated native logs: passed', flush=True)
                before = docker('exec', name, 'python', '-c', "import sqlite3;print(sqlite3.connect('/app/data/frp_agent.db').execute('select count(*) from runtime_samples').fetchone()[0])")
                docker('restart', name)
                binding = json.loads(docker('inspect', name))[0]['NetworkSettings']['Ports']
                client.base_url = f"http://127.0.0.1:{binding['8000/tcp'][0]['HostPort']}"
                for _ in range(90):
                    try:
                        result = client.get('/api/system/overview')
                        if result.status_code == 200 and result.json()['latest']['rdp']['running']:
                            break
                    except httpx.HTTPError:
                        pass
                    time.sleep(.25)
                else:
                    raise AssertionError('Restart did not become ready')
                after = docker('exec', name, 'python', '-c', "import sqlite3;print(sqlite3.connect('/app/data/frp_agent.db').execute('select count(*) from runtime_samples').fetchone()[0])")
                assert int(after) > int(before)
                print('Application restart retains prior samples and resumes collection: passed', flush=True)
        finally:
            subprocess.run(['docker', 'rm', '-f', name], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


if __name__ == '__main__':
    main()
