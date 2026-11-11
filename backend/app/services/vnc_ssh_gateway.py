"""Serve a single screen-sharing connection over an authenticated SSH channel."""
import secrets
import select
import socket
import threading
import time
from contextlib import suppress

from fastapi import HTTPException

from app.database import SessionLocal
from app.models.managed_host import ManagedHost
from app.services.host_access_service import add_audit_log
from app.services.vnc_service import active_vnc_host, challenge_response, open_vnc, read_exact, snapshot


MAX_AGE = 3600
IDLE_TIMEOUT = 900
CHECK_INTERVAL = 5
_slots = threading.BoundedSemaphore(16)


class ScreenSharingCodeError(Exception):
    pass


def authenticate_screen_sharing(inbound, code):
    inbound.settimeout(10)
    inbound.sendall(b'RFB 003.008\n')
    version = read_exact(inbound, 12)
    if version == b'RFB 003.003\n':
        inbound.sendall(b'\0\0\0\x02')
    elif version in (b'RFB 003.007\n', b'RFB 003.008\n'):
        inbound.sendall(b'\x01\x02')
        if read_exact(inbound, 1) != b'\x02':
            raise ValueError('VNC 认证协商失败')
    else:
        raise ValueError('不支持此 VNC 协议版本')
    challenge = secrets.token_bytes(16)
    inbound.sendall(challenge)
    if not secrets.compare_digest(read_exact(inbound, 16, timeout=90), challenge_response(code, challenge)):
        inbound.sendall(b'\0\0\0\x01')
        if version == b'RFB 003.008\n':
            reason = b'Incorrect screen sharing code'
            inbound.sendall(len(reason).to_bytes(4, 'big') + reason)
        raise ScreenSharingCodeError
    inbound.sendall(b'\0' * 4)
    if read_exact(inbound, 1) not in (b'\0', b'\x01'):
        raise ValueError('VNC 客户端初始化失败')


def serve_screen_sharing(inbound, user, host_id, code, ip, enabled, record_failure, relay_lock):
    if not _slots.acquire(blocking=False):
        return
    client = upstream = None
    started = touched = time.monotonic()
    next_check = started
    traffic = [0, 0]
    error = None
    relaying = False
    try:
        with SessionLocal() as db:
            active_vnc_host(db, user, host_id)
        authenticate_screen_sharing(inbound, code)
        if not enabled() or not relay_lock.acquire(blocking=False):
            error = '当前 SSH 通道已有桌面连接或会话已关闭'
            return
        relaying = True
        with SessionLocal() as db:
            host = active_vnc_host(db, user, host_id)
            state = snapshot(db, host)
            client, upstream, initial = open_vnc(db, host)
        with SessionLocal() as db:
            active_vnc_host(db, user, host_id, state)
        if not enabled():
            error = 'SSH 通道已关闭'
            return
        inbound.sendall(initial)
        inbound.settimeout(5)
        upstream.settimeout(5)
        while enabled():
            now = time.monotonic()
            if now - started >= MAX_AGE or now - touched >= IDLE_TIMEOUT:
                break
            if now >= next_check:
                with SessionLocal() as db:
                    active_vnc_host(db, user, host_id, state)
                next_check = now + CHECK_INTERVAL
            ready, _, _ = select.select([inbound, upstream], [], [], 1)
            for source in ready:
                try:
                    data = source.recv(32768)
                except socket.timeout:
                    continue
                if not data:
                    return
                if source is inbound:
                    upstream.sendall(data)
                    traffic[0] += len(data)
                    touched = time.monotonic()
                else:
                    inbound.sendall(data)
                    traffic[1] += len(data)
    except ScreenSharingCodeError:
        record_failure()
        error = '屏幕共享验证码错误'
    except HTTPException as exc:
        error = exc.detail
    except Exception:
        error = '原生 VNC 协商或连接中断'
    finally:
        _slots.release()
        for resource in (upstream, client):
            if resource:
                with suppress(Exception):
                    resource.close()
        if relaying:
            relay_lock.release()
        with SessionLocal() as db:
            host = db.get(ManagedHost, host_id)
            if host:
                add_audit_log(
                    db, host, user, 'vnc_session', 'failed' if error else 'success', ip,
                    target=f'VNC #{host_id}（SSH 网关）', bytes_sent=traffic[0],
                    bytes_received=traffic[1], error=error,
                    duration_ms=int((time.monotonic() - started) * 1000),
                )
