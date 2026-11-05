"""Authenticated, bounded WebSocket to SSH PTY bridge; never records terminal input."""
import asyncio
import json
import logging
import socket
import time
from contextlib import suppress
from urllib.parse import urlsplit

from fastapi import APIRouter, HTTPException, Request, WebSocket, WebSocketDisconnect
from app.auth import get_current_user
from app.database import SessionLocal
from app.models.api_key import ApiKey
from app.models.user import User
from app.services.login_guard import client_address
from app.services.host_access_service import (
    actor_identity, add_audit_log, build_host_client, require_host_access,
)

router = APIRouter()
logger = logging.getLogger(__name__)
_sessions = {}
_pending = 0
MAX_SESSIONS = 16
MAX_PER_USER = 4
MAX_AGE = 3600
IDLE_TIMEOUT = 900
CHECK_INTERVAL = 15


def terminal_size(message):
    return max(2, min(400, int(message.get("cols", 80)))), max(2, min(160, int(message.get("rows", 24))))


def _authenticate(websocket, message, host_id):
    authorization = message.get("authorization", "")
    if message.get("type") != "auth" or not isinstance(authorization, str) or len(authorization) > 8192:
        raise HTTPException(401, "请重新登录后连接 Web SSH")
    scope = {**websocket.scope, "type": "http", "method": "GET", "query_string": b""}
    scope["headers"] = [(k, v) for k, v in scope["headers"] if k.lower() != b"authorization"]
    scope["headers"].append((b"authorization", authorization.encode("latin-1")))
    with SessionLocal() as db:
        user = get_current_user(Request(scope), db)
        host = require_host_access(db, user, host_id, "execute")
        _validate_host(host)
        # Load encrypted credential metadata before detaching from the short-lived session.
        host.credential
        db.expunge_all()
        return user, host


def _validate_host(host):
    if host.host_type != "ssh" or not host.is_active:
        raise HTTPException(403, "仅可连接已启用的 SSH 主机")
    if not host.credential:
        raise HTTPException(400, "主机未配置 SSH 凭据")
    if not host.host_key_fingerprint:
        raise HTTPException(409, "请先在主机列表运行连接测试，记录并核验主机指纹，再使用 Web SSH")


def _still_allowed(user, host):
    with SessionLocal() as db:
        if user.id > 0:
            current = db.get(User, user.id)
            if not current or not current.is_active:
                raise HTTPException(403, "账号已停用，终端连接已结束")
        elif user.id < 0:
            key = db.get(ApiKey, -user.id)
            if not key or not key.is_active or key.is_expired():
                raise HTTPException(403, "API Key 已失效，终端连接已结束")
            current = user
        else:
            current = user
        latest = require_host_access(db, current, host.id, "execute")
        _validate_host(latest)
        if (latest.address, latest.port, latest.credential_id, latest.host_key_fingerprint) != (
            host.address, host.port, host.credential_id, host.host_key_fingerprint
        ):
            raise HTTPException(403, "主机连接配置已变化，请重新连接")


def _audit(user, host, action, status, ip, started, traffic, error=None):
    with SessionLocal() as db:
        add_audit_log(db, host, user, action, status, ip,
            target=f"{host.address}:{host.port}", duration_ms=int((time.monotonic()-started)*1000),
            bytes_sent=traffic[0], bytes_received=traffic[1], error=error)


@router.websocket("/api/managed-hosts/{host_id}/terminal")
async def terminal(websocket: WebSocket, host_id: int):
    global _pending
    origin = urlsplit(websocket.headers.get("origin", ""))
    if (origin.scheme not in ("http", "https") or origin.netloc.lower() != websocket.headers.get("host", "").lower()
            or origin.path or origin.query or origin.fragment):
        await websocket.close(code=1008)
        return
    if host_id < 1 or _pending >= 32 or sum(_sessions.values()) >= MAX_SESSIONS:
        await websocket.close(code=1013)
        return
    _pending += 1
    client = channel = user = host = actor = None
    started = time.monotonic()
    traffic = [0, 0]
    tasks = []
    reason = None
    try:
        await websocket.accept()
        raw = await asyncio.wait_for(websocket.receive_text(), 10)
        if len(raw) > 16384:
            raise ValueError("认证消息过长")
        message = json.loads(raw)
        if not isinstance(message, dict):
            raise ValueError("终端消息格式错误")
        cols, rows = terminal_size(message)
        user, host = await asyncio.to_thread(_authenticate, websocket, message, host_id)
        actor = actor_identity(user)[:2]
        if _sessions.get(actor, 0) >= MAX_PER_USER or sum(_sessions.values()) >= MAX_SESSIONS:
            actor = None
            raise HTTPException(429, "终端会话已达上限，请先关闭其他连接")
        _sessions[actor] = _sessions.get(actor, 0) + 1
        client = build_host_client(host, host.credential)
        await asyncio.wait_for(asyncio.to_thread(client.connect, host.address, host.port, host.credential.username, 15.0), 30)
        channel = await asyncio.wait_for(asyncio.to_thread(client.open_shell, "xterm-256color", cols, rows), 15)
        channel.settimeout(1)
        channel.set_combine_stderr(True)
        await asyncio.to_thread(_audit, user, host, "webssh_connected", "success", client_address(websocket), started, traffic)
        await websocket.send_json({"type": "ready"})
        touched = time.monotonic()
        rendered = asyncio.Event()

        async def output():
            nonlocal touched
            while True:
                try:
                    data = await asyncio.to_thread(channel.recv, 32768)
                except socket.timeout:
                    continue
                if not data:
                    return
                traffic[1] += len(data)
                touched = time.monotonic()
                rendered.clear()
                await websocket.send_bytes(data)
                # Keep one output chunk in flight so a busy shell cannot flood the browser renderer.
                await asyncio.wait_for(rendered.wait(), 30)

        async def inputs():
            nonlocal touched
            while True:
                raw_input = await websocket.receive_text()
                if len(raw_input) > 24576:
                    raise ValueError("终端输入过长")
                packet = json.loads(raw_input)
                if not isinstance(packet, dict):
                    raise ValueError("终端消息格式错误")
                if packet.get("type") == "input" and isinstance(packet.get("data"), str):
                    data = packet["data"].encode("utf-8")
                    if len(data) > 16384:
                        raise ValueError("终端输入过长")
                    await asyncio.to_thread(channel.sendall, data)
                    traffic[0] += len(data)
                    touched = time.monotonic()
                elif packet.get("type") == "ack":
                    rendered.set()
                elif packet.get("type") == "resize":
                    width, height = terminal_size(packet)
                    await asyncio.to_thread(channel.resize_pty, width=width, height=height)
                else:
                    raise ValueError("不支持的终端消息")

        async def monitor():
            while True:
                await asyncio.sleep(CHECK_INTERVAL)
                if time.monotonic()-started > MAX_AGE or time.monotonic()-touched > IDLE_TIMEOUT:
                    raise ValueError("终端会话已超时，请重新连接")
                await asyncio.to_thread(_still_allowed, user, host)

        tasks = [asyncio.create_task(fn()) for fn in (output, inputs, monitor)]
        done, _ = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
        for task in done:
            task.result()
        await websocket.send_json({"type": "exit", "message": "终端会话已结束"})
    except WebSocketDisconnect:
        pass
    except (HTTPException, ValueError, json.JSONDecodeError, asyncio.TimeoutError) as exc:
        reason = (str(exc.detail) if isinstance(exc, HTTPException) else
                  "SSH 连接或终端响应超时，请检查目标主机、网络及代理状态后重试" if isinstance(exc, asyncio.TimeoutError)
                  else str(exc) or "连接失败，请重试")
        with suppress(Exception):
            await websocket.send_json({"type": "error", "message": reason})
    except Exception as exc:
        reason = ("SSH 主机指纹不匹配，连接已阻止；请管理员核实目标机器后更新指纹"
                  if "主机指纹不匹配" in str(exc) else "SSH 连接失败，请检查网络、凭据及主机指纹后重试")
        logger.warning("Web SSH session failed for host %s (%s)", host_id, type(exc).__name__)
        with suppress(Exception):
            await websocket.send_json({"type": "error", "message": reason})
    finally:
        if channel:
            channel.close()
        for task in tasks:
            task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        if client:
            client.close()
        if actor:
            _sessions[actor] -= 1
            if not _sessions[actor]:
                del _sessions[actor]
        _pending -= 1
        if user and host:
            try:
                await asyncio.to_thread(_audit, user, host, "webssh_session", "failed" if reason else "success",
                    client_address(websocket), started, traffic, reason)
            except Exception as audit_error:
                logger.warning("Web SSH audit write failed for host %s (%s)", host_id, type(audit_error).__name__)
        with suppress(Exception):
            await websocket.close(code=1008 if reason else 1000)
