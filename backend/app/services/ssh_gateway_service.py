"""面向系统用户和 API Key 的原生 SSH 跳板服务。"""
from __future__ import annotations

import logging
import os
import socket
import threading
import time
from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple

import paramiko
from sqlalchemy.orm import Session

from app.auth import authenticate_user, verify_api_key
from app.config import get_settings
from app.database import SessionLocal
from app.models.managed_host import ManagedHost
from app.models.user import User
from app.services.host_access_service import (
    active_grant,
    add_audit_log,
    build_host_client,
    is_admin,
)
from app.services.ssh_client import format_host_key_fingerprint

logger = logging.getLogger(__name__)


@dataclass
class GatewayAuthContext:
    user: User
    host_id: int
    host_name: str
    mode: str  # user | api_key


@dataclass
class GatewayChannelRequest:
    event: threading.Event = field(default_factory=threading.Event)
    request_type: Optional[str] = None
    exec_command: Optional[str] = None
    subsystem_name: Optional[str] = None
    pty_requested: bool = False
    pty_term: str = "xterm-256color"
    pty_width: int = 120
    pty_height: int = 40
    upstream_channel: Optional[paramiko.Channel] = None


def parse_gateway_username(username: str) -> Tuple[str, Optional[str], str]:
    """
    解析 SSH 网关用户名。

    - user#host: 系统用户名 + 系统密码
    - host: 主机名 + API Key 作为 SSH 密码
    - apikey#host: 显式 API Key 形式
    """
    value = (username or "").strip()
    if "#" not in value:
        return "api_key", None, value
    identity, host_name = value.split("#", 1)
    if identity.lower() in {"apikey", "api-key"}:
        return "api_key", None, host_name.strip()
    return "user", identity.strip(), host_name.strip()


def authenticate_gateway_login(
    db: Session, gateway_username: str, password: str
) -> Optional[GatewayAuthContext]:
    return authenticate_gateway_resource(
        db, gateway_username, password, host_type="ssh", permission="execute"
    )


def authenticate_gateway_resource(
    db: Session,
    gateway_username: str,
    password: str,
    *,
    host_type: str,
    permission: str,
) -> Optional[GatewayAuthContext]:
    mode, login_name, host_name = parse_gateway_username(gateway_username)
    if not host_name:
        return None

    if mode == "user":
        if not login_name:
            return None
        user = authenticate_user(db, login_name, password)
    else:
        api_key = verify_api_key(db, password)
        user = (
            User(
                id=-api_key.id,
                username=f"api_key_{api_key.id}",
                password_hash="",
                role="api_key",
                is_active=True,
            )
            if api_key
            else None
        )
    if not user:
        return None

    host = (
        db.query(ManagedHost)
        .filter(
            ManagedHost.name == host_name,
            ManagedHost.host_type == host_type,
            ManagedHost.is_active.is_(True),
        )
        .first()
    )
    if not host:
        return None
    if not is_admin(user) and not active_grant(db, user, host.id, permission):
        return None
    return GatewayAuthContext(
        user=user, host_id=host.id, host_name=host.name, mode=mode
    )


class GatewayServerInterface(paramiko.ServerInterface):
    def __init__(self):
        self.auth_context: Optional[GatewayAuthContext] = None
        self._channel_requests: Dict[int, GatewayChannelRequest] = {}
        self._channel_lock = threading.Lock()

    @staticmethod
    def _channel_id(channel) -> int:
        getter = getattr(channel, "get_id", None)
        return int(getter() if getter else channel.chanid)

    def _get_or_create_request(self, channel_id: int) -> GatewayChannelRequest:
        with self._channel_lock:
            request = self._channel_requests.get(channel_id)
            if request is None:
                request = GatewayChannelRequest()
                self._channel_requests[channel_id] = request
            return request

    def get_channel_request(self, channel_id: int) -> GatewayChannelRequest:
        return self._get_or_create_request(channel_id)

    def discard_channel_request(self, channel_id: int) -> None:
        with self._channel_lock:
            self._channel_requests.pop(channel_id, None)

    def get_banner(self):
        return (
            "frp-agent SSH gateway: use user#host with account password, "
            "or host with API Key.\r\n",
            "zh-CN",
        )

    def get_allowed_auths(self, username):
        return "password"

    def check_auth_password(self, username, password):
        db = SessionLocal()
        try:
            self.auth_context = authenticate_gateway_login(db, username, password)
            return (
                paramiko.AUTH_SUCCESSFUL
                if self.auth_context
                else paramiko.AUTH_FAILED
            )
        except Exception:
            logger.exception("SSH 网关认证发生异常")
            return paramiko.AUTH_FAILED
        finally:
            db.close()

    def check_channel_request(self, kind, chanid):
        if kind != "session":
            return paramiko.OPEN_FAILED_ADMINISTRATIVELY_PROHIBITED
        self._get_or_create_request(int(chanid))
        return paramiko.OPEN_SUCCEEDED

    def check_channel_pty_request(
        self, channel, term, width, height, pixelwidth, pixelheight, modes
    ):
        request = self._get_or_create_request(self._channel_id(channel))
        request.pty_term = (
            term.decode("utf-8", errors="replace")
            if isinstance(term, bytes)
            else str(term)
        )
        request.pty_width = max(int(width or 120), 1)
        request.pty_height = max(int(height or 40), 1)
        request.pty_requested = True
        return True

    def check_channel_shell_request(self, channel):
        request = self._get_or_create_request(self._channel_id(channel))
        request.request_type = "shell"
        request.event.set()
        return True

    def check_channel_exec_request(self, channel, command):
        request = self._get_or_create_request(self._channel_id(channel))
        request.request_type = "exec"
        request.exec_command = (
            command.decode("utf-8", errors="replace")
            if isinstance(command, bytes)
            else str(command)
        )
        request.event.set()
        return True

    def check_channel_subsystem_request(self, channel, name):
        request = self._get_or_create_request(self._channel_id(channel))
        subsystem_name = (
            name.decode("utf-8", errors="replace")
            if isinstance(name, bytes)
            else str(name)
        )
        if subsystem_name != "sftp":
            return False
        request.request_type = "subsystem"
        request.subsystem_name = subsystem_name
        request.event.set()
        return True

    def check_channel_window_change_request(
        self, channel, width, height, pixelwidth, pixelheight
    ):
        request = self._get_or_create_request(self._channel_id(channel))
        request.pty_width = max(int(width or request.pty_width), 1)
        request.pty_height = max(int(height or request.pty_height), 1)
        if request.upstream_channel:
            try:
                request.upstream_channel.resize_pty(
                    width=request.pty_width, height=request.pty_height
                )
            except Exception:
                logger.debug("同步 SSH 终端尺寸失败", exc_info=True)
        return True


def _bridge_channels(inbound: paramiko.Channel, upstream: paramiko.Channel):
    def pump(source, target):
        try:
            while True:
                data = source.recv(32768)
                if not data:
                    break
                target.sendall(data)
        except Exception:
            logger.debug("SSH 通道转发结束", exc_info=True)
        finally:
            try:
                target.shutdown_write()
            except Exception:
                pass

    inbound_to_upstream = threading.Thread(
        target=pump,
        args=(inbound, upstream),
        daemon=True,
        name="ssh-gateway-client-to-host",
    )
    def pump_stderr():
        try:
            while True:
                data = upstream.recv_stderr(32768)
                if not data:
                    break
                inbound.send_stderr(data)
        except Exception:
            logger.debug("SSH stderr 转发结束", exc_info=True)

    stderr_thread = threading.Thread(
        target=pump_stderr,
        daemon=True,
        name="ssh-gateway-host-stderr",
    )
    inbound_to_upstream.start()
    stderr_thread.start()
    pump(upstream, inbound)
    inbound_to_upstream.join(timeout=2)
    stderr_thread.join(timeout=2)


class SSHGatewayService:
    def __init__(self):
        self._socket: Optional[socket.socket] = None
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._host_key: Optional[paramiko.PKey] = None

    @property
    def running(self) -> bool:
        return bool(self._thread and self._thread.is_alive())

    @property
    def host_key_fingerprint(self) -> Optional[str]:
        return (
            format_host_key_fingerprint(self._host_key)
            if self._host_key
            else None
        )

    def _load_or_create_host_key(self) -> paramiko.PKey:
        settings = get_settings()
        key_path = os.path.abspath(settings.ssh_gateway_host_key_path)
        os.makedirs(os.path.dirname(key_path), exist_ok=True)
        if os.path.exists(key_path):
            return paramiko.RSAKey.from_private_key_file(key_path)
        key = paramiko.RSAKey.generate(3072)
        key.write_private_key_file(key_path)
        try:
            os.chmod(key_path, 0o600)
        except OSError:
            pass
        logger.warning("已生成新的 SSH 网关主机密钥: %s", key_path)
        return key

    def start(self) -> None:
        settings = get_settings()
        if not settings.ssh_gateway_enabled:
            logger.info("SSH 网关未启用")
            return
        if self.running:
            return
        self._host_key = self._load_or_create_host_key()
        listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        listener.bind((settings.ssh_gateway_host, settings.ssh_gateway_port))
        listener.listen(100)
        listener.settimeout(1.0)
        self._socket = listener
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._accept_loop,
            daemon=True,
            name="ssh-gateway-listener",
        )
        self._thread.start()
        logger.info(
            "SSH 网关已监听 %s:%s",
            settings.ssh_gateway_host,
            settings.ssh_gateway_port,
        )

    def _accept_loop(self):
        listener = self._socket
        while not self._stop_event.is_set():
            try:
                client, address = listener.accept()
            except socket.timeout:
                continue
            except OSError:
                break
            threading.Thread(
                target=self._handle_client,
                args=(client, address),
                daemon=True,
                name=f"ssh-gateway-session-{address[0]}",
            ).start()

    def _handle_channel(
        self,
        inbound: paramiko.Channel,
        server: GatewayServerInterface,
        address,
    ) -> None:
        channel_id = inbound.get_id()
        request = server.get_channel_request(channel_id)
        upstream_client = None
        upstream = None
        started = time.monotonic()
        error_message = None
        try:
            if not request.event.wait(15):
                raise TimeoutError("等待 shell/exec 请求超时")
            if not server.auth_context:
                raise PermissionError("SSH 网关尚未完成认证")

            db = SessionLocal()
            try:
                host = (
                    db.query(ManagedHost)
                    .filter(ManagedHost.id == server.auth_context.host_id)
                    .first()
                )
                if not host or not host.is_active or host.host_type != "ssh":
                    raise ValueError("目标 SSH 主机不存在或已禁用")
                upstream_client = build_host_client(host, host.credential)
                upstream_client.connect(
                    host.address,
                    host.port,
                    host.credential.username,
                    timeout=15.0,
                )
                if request.request_type == "exec":
                    open_exec = getattr(upstream_client, "open_exec_channel", None)
                    if not open_exec:
                        raise RuntimeError("SSH 客户端不支持 exec 请求")
                    upstream = open_exec(
                        request.exec_command or "",
                        request_pty=request.pty_requested,
                        term=request.pty_term,
                        width=request.pty_width,
                        height=request.pty_height,
                    )
                elif request.request_type == "shell":
                    open_shell = getattr(upstream_client, "open_shell", None)
                    if not open_shell:
                        raise RuntimeError("SSH 客户端不支持交互式 shell")
                    upstream = open_shell(
                        term=request.pty_term,
                        width=request.pty_width,
                        height=request.pty_height,
                    )
                elif request.request_type == "subsystem":
                    open_subsystem = getattr(
                        upstream_client, "open_subsystem_channel", None
                    )
                    if not open_subsystem:
                        raise RuntimeError("SSH 客户端不支持 SFTP 子系统转发")
                    upstream = open_subsystem(request.subsystem_name or "")
                else:
                    raise RuntimeError("不支持的 SSH channel 请求")
                request.upstream_channel = upstream
            finally:
                db.close()

            _bridge_channels(inbound, upstream)
            if request.request_type == "exec" and upstream.exit_status_ready():
                try:
                    inbound.send_exit_status(upstream.recv_exit_status())
                except Exception:
                    pass
        except Exception as exc:
            error_message = str(exc)
            logger.warning(
                "SSH 网关通道失败 (%s, channel=%s): %s",
                address[0],
                channel_id,
                exc,
            )
            try:
                inbound.sendall(f"\r\nGateway error: {exc}\r\n".encode("utf-8"))
            except Exception:
                pass
        finally:
            duration_ms = int((time.monotonic() - started) * 1000)
            if server.auth_context:
                db = SessionLocal()
                try:
                    host = (
                        db.query(ManagedHost)
                        .filter(ManagedHost.id == server.auth_context.host_id)
                        .first()
                    )
                    if host:
                        add_audit_log(
                            db,
                            host,
                            server.auth_context.user,
                            "ssh_gateway_session",
                            "failed" if error_message else "success",
                            address[0],
                            target=f"{host.address}:{host.port}",
                            command=(
                                request.exec_command
                                or (
                                    f"subsystem:{request.subsystem_name}"
                                    if request.subsystem_name
                                    else None
                                )
                            ),
                            duration_ms=duration_ms,
                            error=error_message,
                        )
                except Exception:
                    logger.exception("写入 SSH 网关审计失败")
                finally:
                    db.close()
            for resource in (upstream, inbound):
                if resource:
                    try:
                        resource.close()
                    except Exception:
                        pass
            if upstream_client:
                upstream_client.close()
            server.discard_channel_request(channel_id)

    def _handle_client(self, client_socket: socket.socket, address):
        transport = None
        server = GatewayServerInterface()
        workers = []
        try:
            transport = paramiko.Transport(client_socket)
            transport.local_version = "SSH-2.0-frp-agent-gateway"
            transport.add_server_key(self._host_key)
            transport.start_server(server=server)
            while transport.is_active() and not self._stop_event.is_set():
                inbound = transport.accept(1)
                if inbound is None:
                    workers = [worker for worker in workers if worker.is_alive()]
                    continue
                if not server.auth_context:
                    inbound.close()
                    raise PermissionError("SSH 网关尚未完成认证")
                worker = threading.Thread(
                    target=self._handle_channel,
                    args=(inbound, server, address),
                    daemon=True,
                    name=f"ssh-gateway-channel-{address[0]}-{inbound.get_id()}",
                )
                worker.start()
                workers.append(worker)
        except Exception as exc:
            logger.warning("SSH 网关连接失败 (%s): %s", address[0], exc)
        finally:
            if transport:
                transport.close()
            for worker in workers:
                worker.join(timeout=2)
            try:
                client_socket.close()
            except Exception:
                pass

    def stop(self) -> None:
        self._stop_event.set()
        listener = self._socket
        if listener:
            try:
                listener.close()
            except OSError:
                pass
        if self._thread:
            self._thread.join(timeout=3)
            self._thread = None
        self._socket = None


ssh_gateway_service = SSHGatewayService()
