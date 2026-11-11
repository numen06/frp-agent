"""VNC password delegation over a trusted direct connection or a pinned SSH tunnel."""
import os
import struct
import time
import socket
import ipaddress
from fastapi import HTTPException
from cryptography.hazmat.primitives.ciphers import Cipher, modes
try:
    from cryptography.hazmat.decrepit.ciphers.algorithms import TripleDES
except ImportError:
    from cryptography.hazmat.primitives.ciphers.algorithms import TripleDES
from app.models.managed_host import ManagedHost
from app.models.api_key import ApiKey
from app.models.ssh_credential import SshCredential
from app.models.user import User
from app.services.credential_encryption import decrypt_secret
from app.services.host_access_service import build_host_client, require_host_access
from app.services.ssh_client import CommandResult


TRUSTED_NETWORKS = tuple(ipaddress.ip_network(value) for value in (
    '127.0.0.0/8', '10.0.0.0/8', '172.16.0.0/12', '192.168.0.0/16', '100.64.0.0/10', '::1/128', 'fc00::/7'))


def validate_host(host):
    if host.host_type != 'vnc' or not host.is_active:
        raise HTTPException(403, '仅可连接已启用的 VNC 主机')


def active_vnc_host(db, user, host_id, state=None):
    current = user
    if user.id > 0:
        current = db.get(User, user.id)
        if not current or not current.is_active:
            raise HTTPException(403, '账号已停用')
    elif user.id < 0:
        key = db.get(ApiKey, -user.id)
        if not key or not key.is_active or key.is_expired():
            raise HTTPException(403, 'API Key 已失效')
    host = require_host_access(db, current, host_id, 'connect')
    validate_host(host)
    if state is not None and snapshot(db, host) != state:
        raise HTTPException(403, '主机或凭据已变化，请重新连接')
    return host


def trusted_ip(value):
    ip = ipaddress.ip_address(value)
    if getattr(ip, 'ipv4_mapped', None):
        ip = ip.ipv4_mapped
    return any(ip in network for network in TRUSTED_NETWORKS)


def direct_address(address):
    address = address.strip()
    if not address or any(c in address for c in '/@?#\\') or '%' in address:
        raise HTTPException(400, 'VNC 地址请填写主机名或 IP')
    try:
        ipaddress.ip_address(address)
    except ValueError:
        return address
    if not trusted_ip(address):
        raise HTTPException(400, '传统 VNC 直连没有传输加密，请使用可信内网、VPN 或 FRP 的内部/回环入口；公网目标可选 SSH 隧道')
    return address


def open_direct(address, port):
    rows = socket.getaddrinfo(address, port, type=socket.SOCK_STREAM)
    if not rows or any(not trusted_ip(row[4][0]) for row in rows):
        raise HTTPException(400, 'VNC 域名解析到非可信网络地址，已拒绝发送凭据；请使用 VPN、FRP 内部入口或 SSH 隧道')
    last_error = None
    for family, kind, protocol, _, endpoint in rows:
        channel = socket.socket(family, kind, protocol)
        try:
            channel.settimeout(10)
            # Connect the validated numeric address, preventing DNS rebinding.
            channel.connect(endpoint)
            return channel
        except OSError as exc:
            channel.close()
            last_error = exc
    raise last_error


def validate_vnc_values(db, values):
    credential = db.get(SshCredential, values.get('credential_id')) if values.get('credential_id') else None
    if not credential or credential.auth_type != 'password':
        raise HTTPException(400, 'VNC 必须绑定密码凭据')
    password = decrypt_secret(credential.password_encrypted)
    # Classic VNC silently truncates at 8 bytes; reject rather than hide this limitation.
    if not password or not password.isascii() or not 1 <= len(password) <= 8:
        raise HTTPException(400, '传统 VNC 密码必须为 1–8 位 ASCII 字符；请使用专用凭据')
    if values.get('vnc_ssh_host_id'):
        if values.get('address') != '127.0.0.1':
            raise HTTPException(400, 'SSH 隧道内的 VNC 目标必须为 127.0.0.1')
        validate_ssh(db.get(ManagedHost, values['vnc_ssh_host_id']))
    else:
        values['address'] = direct_address(values['address'])
    values['docker_credential_id'] = None
    values['docker_endpoint_id'] = None
    values['host_key_fingerprint'] = None


def validate_ssh(ssh):
    if not ssh or ssh.host_type != 'ssh' or not ssh.is_active or not ssh.credential or not ssh.host_key_fingerprint:
        raise HTTPException(409, '请绑定已启用、已配置凭据并核验 SSH 指纹的 Mac SSH 主机')


def snapshot(db, host):
    values = {k: getattr(host, k) for k in ('address', 'credential_id', 'vnc_ssh_host_id')}
    validate_vnc_values(db, values)
    # Include encrypted values, so changing a credential also revokes an active session.
    def cred(c):
        return (c.id, c.username, c.auth_type, c.password_encrypted, c.private_key_encrypted, c.passphrase_encrypted)
    if not host.vnc_ssh_host_id:
        return ('direct', host.address, host.port, cred(host.credential))
    ssh = db.get(ManagedHost, host.vnc_ssh_host_id)
    return (host.address, host.port, cred(host.credential), ssh.id, ssh.address, ssh.port,
            ssh.host_key_fingerprint, cred(ssh.credential))


def read_exact(channel, size, timeout=10):
    data = bytearray()
    deadline = time.monotonic() + timeout
    while len(data) < size:
        channel.settimeout(max(.01, deadline - time.monotonic()))
        chunk = channel.recv(size-len(data))
        if not chunk or time.monotonic() > deadline:
            raise ValueError('VNC 握手未完成')
        data.extend(chunk)
    return bytes(data)


def challenge_response(password, challenge):
    key = bytes(int(f'{b:08b}'[::-1], 2) for b in password.encode('ascii').ljust(8, b'\0'))
    encryptor = Cipher(TripleDES(key * 3), modes.ECB()).encryptor()
    return encryptor.update(challenge) + encryptor.finalize()


def authenticate_vnc(channel, password):
    banner = read_exact(channel, 12)
    if banner[:8] != b'RFB 003.' or banner[-1:] != b'\n' or not banner[8:11].isdigit():
        raise ValueError('目标不是有效的 VNC 服务')
    minor = int(banner[8:11])
    version = 8 if minor >= 8 else 7 if minor >= 7 else 3
    channel.sendall(f'RFB 003.{version:03d}\n'.encode())
    if version == 3:
        if struct.unpack('!I', read_exact(channel, 4))[0] != 2:
            raise ValueError('VNC 必须启用密码认证，拒绝无认证连接')
    else:
        count = read_exact(channel, 1)[0]
        types = read_exact(channel, count)
        if 2 not in types:
            raise ValueError('请在 Mac 屏幕共享中启用 VNC 密码控制；不接受无认证连接')
        channel.sendall(b'\x02')
    channel.sendall(challenge_response(password, read_exact(channel, 16)))
    if read_exact(channel, 4) != b'\0\0\0\0':
        raise ValueError('VNC 密码认证失败，请检查专用 VNC 密码')
    channel.sendall(b'\x01')  # shared desktop, do not evict other users
    header = read_exact(channel, 24)
    name_length = struct.unpack('!I', header[20:24])[0]
    width, height = struct.unpack('!HH', header[:4])
    if name_length > 4096 or not width or not height or width * height > 33554432:
        raise ValueError('VNC 桌面参数超出限制')
    return header + read_exact(channel, name_length)


def open_vnc(db, host):
    snapshot(db, host)
    from app.services.host_discovery import check_upstream
    client = channel = None
    try:
        if host.vnc_ssh_host_id:
            ssh = db.get(ManagedHost, host.vnc_ssh_host_id)
            check_upstream(db, ssh)
            client = build_host_client(ssh, ssh.credential)
            client.connect(ssh.address, ssh.port, ssh.credential.username, 10)
            channel = client.open_loopback_channel(host.port)
        else:
            proxy = check_upstream(db, host)
            address = host.address
            # A separate desktop worker reaches the local FRP node via its private address.
            if proxy and proxy.frps_server.is_builtin and address.lower() in ('127.0.0.1', 'localhost', '::1'):
                address = os.environ.get('FRP_LOCAL_ADDRESS') or address
            try:
                client = channel = open_direct(address, host.port)
            except OSError as exc:
                raise HTTPException(502, 'VNC 端口无法连接，请检查地址、端口和 FRP 转发') from exc
        initial = authenticate_vnc(channel, decrypt_secret(host.credential.password_encrypted))
        channel.settimeout(1)
        return client, channel, initial
    except BaseException:
        if channel:
            channel.close()
        if client: client.close()
        raise


def test_vnc_connection(db, host):
    started = time.monotonic()
    client, channel, _ = open_vnc(db, host)
    channel.close()
    client.close()
    mode = 'SSH 指纹、加密通道及' if host.vnc_ssh_host_id else '可信网络直连及'
    return CommandResult(0, mode + ' VNC 密码认证通过；桌面显示以实际连接为准', ''), int((time.monotonic()-started)*1000)
