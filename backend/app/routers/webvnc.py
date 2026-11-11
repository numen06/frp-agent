"""Same-origin WSS VNC bridge. Platform auth precedes any upstream connection."""
import asyncio
import json
import logging
import socket
import time
from contextlib import suppress
from urllib.parse import urlsplit
from fastapi import APIRouter, Depends, HTTPException, Request, Response, WebSocket, WebSocketDisconnect
from app.auth import get_current_user
from app.config import get_settings
from app.database import SessionLocal, get_db
from app.services.vnc_gateway_service import vnc_gateway_service
from app.services.host_access_service import actor_identity, require_host_access, add_audit_log
from app.services.login_guard import client_address
from app.services.vnc_service import active_vnc_host, open_vnc, snapshot, validate_host

logger = logging.getLogger(__name__)
router = APIRouter()
_sessions = {}
_pending = 0
MAX_SESSIONS = 16
MAX_PER_USER = 2
CHECK_INTERVAL = 5
MAX_AGE = 3600
IDLE_TIMEOUT = 900


@router.post("/api/managed-hosts/{host_id}/vnc-ticket")
def native_ticket(host_id: int, request: Request, response: Response,
                  user=Depends(get_current_user), db=Depends(get_db)):
    if request.url.scheme != "https" or not request.headers.get("authorization", "").startswith("Basic "):
        raise HTTPException(403, "请通过 HTTPS 使用平台账号登录")
    if user.id <= 0:
        raise HTTPException(403, "请使用平台账号签发连接凭据")
    settings = get_settings()
    hostname = request.url.hostname
    if hostname and ":" in hostname:
        hostname = f"[{hostname}]"
    address = settings.vnc_gateway_public_address or f"{hostname}:{settings.vnc_gateway_port}"
    response.headers["Cache-Control"] = "no-store"
    return vnc_gateway_service.issue(db, user, host_id, f"vnc://{address}", client_address(request))


def authenticate(ws, packet, host_id):
    authorization = packet.get('authorization', '')
    if packet.get('type') != 'auth' or not isinstance(authorization, str) or len(authorization) > 8192:
        raise HTTPException(401, '请重新登录后连接 VNC')
    scope = {**ws.scope, 'type': 'http', 'method': 'GET', 'query_string': b''}
    scope['headers'] = [(k,v) for k,v in scope['headers'] if k.lower() != b'authorization']
    scope['headers'].append((b'authorization', authorization.encode('latin-1')))
    with SessionLocal() as db:
        user = get_current_user(Request(scope), db)
        host = require_host_access(db, user, host_id, 'connect')
        validate_host(host)
        state = snapshot(db, host)
        db.expunge_all()
        return user, host, state


def connect_upstream(user, host, state):
    still_allowed(user, host, state)
    with SessionLocal() as db:
        latest = db.get(type(host), host.id)
        validate_host(latest)
        if snapshot(db, latest) != state:
            raise HTTPException(403, "主机配置已变化")
        return open_vnc(db, latest)


def still_allowed(user, host, state):
    with SessionLocal() as db:
        active_vnc_host(db, user, host.id, state)


def audit(user, host, action, status, ip, started, traffic, error=None):
    with SessionLocal() as db:
        add_audit_log(db, host, user, action, status, ip, target=f'VNC #{host.id}',
                      duration_ms=int((time.monotonic()-started)*1000),
                      bytes_sent=traffic[0], bytes_received=traffic[1], error=error)


@router.websocket('/api/managed-hosts/{host_id}/vnc')
async def desktop(ws: WebSocket, host_id: int):
    global _pending
    origin = urlsplit(ws.headers.get('origin', ''))
    # Encrypted browser transport is mandatory; proxy must preserve Origin and Host.
    if (ws.url.scheme != 'wss' or origin.scheme != 'https' or origin.netloc.lower() != ws.headers.get('host','').lower()
            or origin.path or origin.query or origin.fragment or ws.query_params):
        await ws.close(code=1008); return
    if host_id < 1 or _pending >= 32 or sum(_sessions.values()) >= MAX_SESSIONS:
        await ws.close(code=1013); return
    _pending += 1
    user = host = actor = client = channel = None
    tasks = []
    started = touched = time.monotonic()
    traffic = [0, 0]
    reason = None
    binary_started = False
    try:
        await ws.accept()
        raw = await asyncio.wait_for(ws.receive_text(), 10)
        if len(raw) > 16384:
            raise ValueError('认证消息过长')
        packet = json.loads(raw)
        if not isinstance(packet, dict):
            raise ValueError('认证消息无效')
        user, host, state = await asyncio.to_thread(authenticate, ws, packet, host_id)
        key = actor_identity(user)[:2]
        if _sessions.get(key, 0) >= MAX_PER_USER or sum(_sessions.values()) >= MAX_SESSIONS:
            raise HTTPException(429, 'VNC 会话已达上限')
        actor = key
        _sessions[actor] = _sessions.get(actor, 0) + 1
        opening = asyncio.create_task(asyncio.to_thread(connect_upstream, user, host, state))
        try:
            client, channel, initial = await asyncio.shield(opening)
        except asyncio.CancelledError:
            # A worker thread cannot be cancelled: reclaim its result if shutdown
            # interrupts SSH negotiation before this coroutine owns the sockets.
            def reclaim(task):
                try:
                    opened_client, opened_channel, _ = task.result()
                    opened_channel.close()
                    opened_client.close()
                except Exception:
                    pass
            opening.add_done_callback(reclaim)
            raise
        await asyncio.to_thread(still_allowed, user, host, state)
        await ws.send_json({'type': 'ready'})
        binary_started = True
        # Browser sees a fresh RFB handshake; upstream credentials never cross WSS.
        buffer = bytearray()
        async def read_browser(size):
            while len(buffer) < size:
                data = await asyncio.wait_for(ws.receive_bytes(), 10)
                if not data or len(data) + len(buffer) > 65536:
                    raise ValueError('VNC 数据过长')
                buffer.extend(data)
            result = bytes(buffer[:size]); del buffer[:size]
            return result
        await ws.send_bytes(b'RFB 003.008\n')
        if await read_browser(12) != b'RFB 003.008\n':
            raise ValueError('VNC 协议版本无效')
        await ws.send_bytes(b'\x01\x01')
        if await read_browser(1) != b'\x01':
            raise ValueError('VNC 协商无效')
        await ws.send_bytes(b'\0\0\0\0')
        if await read_browser(1) != b'\x01':
            raise ValueError('仅支持共享桌面')
        await ws.send_bytes(initial)
        await asyncio.to_thread(audit, user, host, 'vnc_connected', 'success', client_address(ws), started, traffic)
        async def output():
            while True:
                try:
                    data = await asyncio.to_thread(channel.recv, 32768)
                except socket.timeout:
                    continue
                if not data: return
                traffic[1] += len(data)
                await asyncio.wait_for(ws.send_bytes(data), 30)
        async def inputs():
            nonlocal touched
            if buffer:
                await asyncio.to_thread(channel.sendall, bytes(buffer))
                traffic[0] += len(buffer)
                buffer.clear()
            while True:
                data = await ws.receive_bytes()
                if not data or len(data) > 65536:
                    raise ValueError('VNC 数据过长')
                await asyncio.to_thread(channel.sendall, data)
                traffic[0] += len(data)
                touched = time.monotonic()
        async def monitor():
            while True:
                await asyncio.sleep(CHECK_INTERVAL)
                if time.monotonic()-started > MAX_AGE or time.monotonic()-touched > IDLE_TIMEOUT:
                    raise ValueError('VNC 会话已超时')
                await asyncio.to_thread(still_allowed, user, host, state)
        tasks = [asyncio.create_task(fn()) for fn in (output, inputs, monitor)]
        done, _ = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
        for task in done: task.result()
    except WebSocketDisconnect:
        pass
    except Exception as exc:
        reason = exc.detail if isinstance(exc, HTTPException) else 'VNC 连接失败或已结束，请检查授权、SSH 指纹及 VNC 密码'
        if not binary_started:
            with suppress(Exception):
                await ws.send_json({'type': 'error', 'message': reason})
    finally:
        if channel: channel.close()
        if client: client.close()
        for task in tasks: task.cancel()
        if tasks: await asyncio.gather(*tasks, return_exceptions=True)
        if actor:
            _sessions[actor] -= 1
            if not _sessions[actor]: del _sessions[actor]
        _pending -= 1
        if user and host:
            try:
                await asyncio.to_thread(audit, user, host, 'vnc_session', 'failed' if reason else 'success', client_address(ws), started, traffic, reason)
            except Exception as exc:
                logger.warning("VNC audit failed for host %s (%s)", host_id, type(exc).__name__)
        with suppress(Exception):
            await ws.close(code=1008 if reason else 1000)
