"""VNC password delegation inside a pinned SSH channel to the Mac's loopback only."""
import struct
import time
from fastapi import HTTPException
from cryptography.hazmat.primitives.ciphers import Cipher, modes
try:
    from cryptography.hazmat.decrepit.ciphers.algorithms import TripleDES
except ImportError:
    from cryptography.hazmat.primitives.ciphers.algorithms import TripleDES
from app.models.managed_host import ManagedHost
from app.models.ssh_credential import SshCredential
from app.services.credential_encryption import decrypt_secret
from app.services.host_access_service import build_host_client
from app.services.ssh_client import CommandResult


def validate_vnc_values(db, values):
    if values.get('address') != '127.0.0.1':
        raise HTTPException(400, 'VNC 地址必须为 127.0.0.1，目标通过关联的 Mac SSH 主机确定')
    credential = db.get(SshCredential, values.get('credential_id')) if values.get('credential_id') else None
    if not credential or credential.auth_type != 'password':
        raise HTTPException(400, 'VNC 必须绑定密码凭据')
    password = decrypt_secret(credential.password_encrypted)
    # Classic VNC silently truncates at 8 bytes; reject rather than hide this limitation.
    if not password or not password.isascii() or not 1 <= len(password) <= 8:
        raise HTTPException(400, '传统 VNC 密码必须为 1–8 位 ASCII 字符；请使用专用凭据')
    ssh = db.get(ManagedHost, values.get('vnc_ssh_host_id')) if values.get('vnc_ssh_host_id') else None
    validate_ssh(ssh)
    values['docker_credential_id'] = None
    values['docker_endpoint_id'] = None
    values['host_key_fingerprint'] = None


def validate_ssh(ssh):
    if not ssh or ssh.host_type != 'ssh' or not ssh.is_active or not ssh.credential or not ssh.host_key_fingerprint:
        raise HTTPException(409, '请绑定已启用、已配置凭据并核验 SSH 指纹的 Mac SSH 主机')


def snapshot(db, host):
    values = {k: getattr(host, k) for k in ('address', 'credential_id', 'vnc_ssh_host_id')}
    validate_vnc_values(db, values)
    ssh = db.get(ManagedHost, host.vnc_ssh_host_id)
    # Include encrypted values, so changing a credential also revokes an active session.
    def cred(c):
        return (c.id, c.username, c.auth_type, c.password_encrypted, c.private_key_encrypted, c.passphrase_encrypted)
    return (host.address, host.port, cred(host.credential), ssh.id, ssh.address, ssh.port,
            ssh.host_key_fingerprint, cred(ssh.credential))


def read_exact(channel, size):
    data = bytearray()
    deadline = time.monotonic() + 10
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
    ssh = db.get(ManagedHost, host.vnc_ssh_host_id)
    from app.services.host_discovery import check_upstream
    check_upstream(db, ssh)
    client = build_host_client(ssh, ssh.credential)
    channel = None
    try:
        client.connect(ssh.address, ssh.port, ssh.credential.username, 10)
        channel = client.open_loopback_channel(host.port)
        initial = authenticate_vnc(channel, decrypt_secret(host.credential.password_encrypted))
        channel.settimeout(1)
        return client, channel, initial
    except BaseException:
        if channel:
            channel.close()
        client.close()
        raise


def test_vnc_connection(db, host):
    started = time.monotonic()
    client, channel, _ = open_vnc(db, host)
    channel.close()
    client.close()
    return CommandResult(0, 'SSH 指纹、加密通道及 VNC 密码认证通过；桌面显示以实际连接为准', ''), int((time.monotonic()-started)*1000)
