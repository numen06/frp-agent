"""面向系统用户和 API Key 的原生 SSH 跳板服务。"""
from __future__ import annotations

import logging
import ipaddress
import json
import os
import socket
import tempfile
import threading
import time
from collections import OrderedDict, deque
from dataclasses import dataclass, field
from typing import Callable, Deque, Dict, Optional, Tuple

import paramiko
from sqlalchemy.orm import Session

from app.auth import authenticate_user, verify_api_key
from app.config import get_settings
from app.database import SessionLocal
from app.models.managed_host import ManagedHost
from app.models.user import User
from app.services.credential_encryption import decrypt_secret
from app.services.host_access_service import (
    active_grant,
    add_audit_log,
    build_host_client,
    is_admin,
)
from app.services.ssh_client import format_host_key_fingerprint

logger = logging.getLogger(__name__)

MAX_GATEWAY_SESSIONS = 64
MAX_GATEWAY_SESSIONS_PER_IP = 24
MAX_AUTH_FAILURES = 3
AUTH_DEADLINE_SECONDS = 20
HANDSHAKE_TIMEOUT_SECONDS = 10
AUTH_FAILURE_WINDOW_SECONDS = 300
AUTH_FAILURE_BAN_THRESHOLD = 10
AUTH_BAN_SECONDS = 1800
MAX_TRACKED_AUTH_IPS = 4096


def _gateway_sudo_password(host, user: User) -> Optional[str]:
    if not is_admin(user):
        return None
    credential = host.credential
    encrypted = credential.sudo_password_encrypted
    if not encrypted and credential.auth_type == "password":
        encrypted = credential.password_encrypted
    return decrypt_secret(encrypted)


def _prepare_gateway_exec(host, user: User, command: str):
    if command.strip() != "sudo -i":
        return command, None
    password = _gateway_sudo_password(host, user)
    return ("sudo -S -p '' -i", password) if password else (command, None)


def _prime_interactive_sudo(upstream: paramiko.Channel, password: str) -> bool:
    marker = b"[frp-agent-sudo]"
    ready_marker = b"[frp-agent-sudo-ready]"
    command = (
        b"/usr/bin/sudo -n -v >/dev/null 2>&1 && "
        b"printf '\\133frp-agent-sudo-ready\\135' || "
        b"/usr/bin/sudo -S -p \"$(printf '\\133frp-agent-sudo\\135')\" -v\n"
    )
    upstream.sendall(command)
    deadline = time.monotonic() + 5
    response = bytearray()
    while time.monotonic() < deadline:
        if not upstream.recv_ready():
            time.sleep(0.02)
            continue
        data = upstream.recv(32768)
        if not data:
            break
        response.extend(data)
        if ready_marker in response:
            return True
        if marker in response:
            upstream.sendall(f"{password}\n".encode("utf-8"))
            return True
    return False


@dataclass
class GatewayAuthContext:
    user: User
    host_id: int
    host_name: str
    mode: str  # user | api_key | public_key


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


@dataclass
class _AuthFailureState:
    attempts: Deque[float] = field(default_factory=deque)
    blocked_until: float = 0.0


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

    return _authorize_gateway_identity(
        db, user, host_name, mode=mode, host_type=host_type, permission=permission
    )


def _authorize_gateway_identity(
    db: Session,
    user: User,
    host_name: str,
    *,
    mode: str,
    host_type: str,
    permission: str,
) -> Optional[GatewayAuthContext]:

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


def authenticate_gateway_public_key(
    db: Session, gateway_username: str, key: paramiko.PKey
) -> Optional[GatewayAuthContext]:
    mode, login_name, host_name = parse_gateway_username(gateway_username)
    if mode != "user" or not login_name or not host_name:
        return None
    public_key = f"{key.get_name()} {key.get_base64()}"
    user = (
        db.query(User)
        .filter(
            User.username == login_name,
            User.ssh_public_key == public_key,
            User.is_active.is_(True),
        )
        .first()
    )
    if not user:
        return None
    return _authorize_gateway_identity(
        db,
        user,
        host_name,
        mode="public_key",
        host_type="ssh",
        permission="execute",
    )


class GatewayServerInterface(paramiko.ServerInterface):
    def __init__(
        self,
        on_auth_failure: Optional[Callable[[], None]] = None,
        on_auth_success: Optional[Callable[[], None]] = None,
    ):
        self.auth_context: Optional[GatewayAuthContext] = None
        self.failed_auth_attempts = 0
        self._on_auth_failure = on_auth_failure
        self._on_auth_success = on_auth_success
        self._channel_requests: Dict[int, GatewayChannelRequest] = {}
        self._channel_lock = threading.Lock()

    def _auth_result(self, context: Optional[GatewayAuthContext]):
        self.auth_context = context
        if context:
            if self._on_auth_success:
                self._on_auth_success()
            return paramiko.AUTH_SUCCESSFUL
        self.failed_auth_attempts += 1
        if self._on_auth_failure:
            self._on_auth_failure()
        return paramiko.AUTH_FAILED

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
            "frp-agent SSH gateway: use user#host with account password/public key, "
            "or host with API Key.\r\n",
            "zh-CN",
        )

    def get_allowed_auths(self, username):
        return "publickey,password"

    def check_auth_password(self, username, password):
        if self.failed_auth_attempts >= MAX_AUTH_FAILURES:
            return paramiko.AUTH_FAILED
        db = SessionLocal()
        try:
            return self._auth_result(
                authenticate_gateway_login(db, username, password)
            )
        except Exception:
            self.failed_auth_attempts += 1
            if self._on_auth_failure:
                self._on_auth_failure()
            logger.exception("SSH 网关认证发生异常")
            return paramiko.AUTH_FAILED
        finally:
            db.close()

    def check_auth_publickey(self, username, key):
        if self.failed_auth_attempts >= MAX_AUTH_FAILURES:
            return paramiko.AUTH_FAILED
        db = SessionLocal()
        try:
            return self._auth_result(
                authenticate_gateway_public_key(db, username, key)
            )
        except Exception:
            self.failed_auth_attempts += 1
            if self._on_auth_failure:
                self._on_auth_failure()
            logger.exception("SSH 网关公钥认证发生异常")
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
        self._sessions_lock = threading.Lock()
        self._active_sessions = 0
        self._sessions_by_ip: Dict[str, int] = {}
        self._auth_lock = threading.Lock()
        self._auth_by_ip: OrderedDict[str, _AuthFailureState] = OrderedDict()
        self._ban_file_path: Optional[str] = None

    def _load_bans(self) -> None:
        path = self._ban_file_path
        if not path or not os.path.exists(path):
            return
        try:
            if os.path.getsize(path) > 1_000_000:
                raise ValueError("SSH 网关封禁名单文件过大")
            with open(path, "r", encoding="utf-8") as handle:
                payload = json.load(handle)
            if (
                not isinstance(payload, dict)
                or payload.get("version") != 1
                or not isinstance(payload.get("bans"), dict)
            ):
                raise ValueError("SSH 网关封禁名单格式无效")
            now = time.time()
            needs_cleanup = False
            with self._auth_lock:
                for ip, until in payload["bans"].items():
                    if len(self._auth_by_ip) >= MAX_TRACKED_AUTH_IPS:
                        needs_cleanup = True
                        break
                    try:
                        ipaddress.ip_address(ip)
                        until = float(until)
                    except (ValueError, TypeError):
                        needs_cleanup = True
                        continue
                    if until > now:
                        self._auth_by_ip[ip] = _AuthFailureState(blocked_until=until)
                    else:
                        needs_cleanup = True
                if needs_cleanup:
                    self._persist_bans_locked()
            logger.info("已恢复 %s 个 SSH 网关临时封禁来源", len(self._auth_by_ip))
        except (OSError, ValueError, TypeError):
            logger.exception("加载 SSH 网关封禁名单失败: %s", path)

    def _persist_bans_locked(self) -> None:
        path = self._ban_file_path
        if not path:
            return
        now = time.time()
        payload = {
            "version": 1,
            "bans": {
                ip: state.blocked_until
                for ip, state in self._auth_by_ip.items()
                if state.blocked_until > now
            },
        }
        temporary_path = None
        try:
            directory = os.path.dirname(path)
            os.makedirs(directory, exist_ok=True)
            fd, temporary_path = tempfile.mkstemp(
                prefix=".ssh_gateway_bans-", dir=directory
            )
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(payload, handle, ensure_ascii=False, separators=(",", ":"))
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary_path, path)
        except OSError:
            logger.exception("保存 SSH 网关封禁名单失败: %s", path)
            if temporary_path:
                try:
                    os.unlink(temporary_path)
                except OSError:
                    pass

    def _is_ip_blocked(self, ip: str) -> bool:
        now = time.monotonic()
        wall_now = time.time()
        with self._auth_lock:
            state = self._auth_by_ip.get(ip)
            if not state:
                return False
            if state.blocked_until > wall_now:
                return True
            if state.blocked_until:
                del self._auth_by_ip[ip]
                self._persist_bans_locked()
                return False
            while state.attempts and now - state.attempts[0] > AUTH_FAILURE_WINDOW_SECONDS:
                state.attempts.popleft()
            if not state.attempts:
                del self._auth_by_ip[ip]
            return False

    def _record_auth_failure(self, ip: str) -> None:
        now = time.monotonic()
        wall_now = time.time()
        newly_blocked = False
        with self._auth_lock:
            state = self._auth_by_ip.get(ip)
            if state is None:
                if len(self._auth_by_ip) >= MAX_TRACKED_AUTH_IPS:
                    self._auth_by_ip.popitem(last=False)
                state = _AuthFailureState()
                self._auth_by_ip[ip] = state
            else:
                self._auth_by_ip.move_to_end(ip)
            if state.blocked_until > wall_now:
                return
            if state.blocked_until:
                state.blocked_until = 0.0
                state.attempts.clear()
            while state.attempts and now - state.attempts[0] > AUTH_FAILURE_WINDOW_SECONDS:
                state.attempts.popleft()
            state.attempts.append(now)
            if len(state.attempts) >= AUTH_FAILURE_BAN_THRESHOLD:
                state.attempts.clear()
                state.blocked_until = wall_now + AUTH_BAN_SECONDS
                self._persist_bans_locked()
                newly_blocked = True
        if newly_blocked:
            logger.warning("SSH 网关临时封禁来源 %s，持续 %s 秒", ip, AUTH_BAN_SECONDS)

    def _clear_auth_failures(self, ip: str) -> None:
        with self._auth_lock:
            state = self._auth_by_ip.get(ip)
            if state and not state.blocked_until:
                self._auth_by_ip.pop(ip, None)

    def _reserve_session(self, address) -> bool:
        ip = address[0]
        with self._sessions_lock:
            if self._active_sessions >= MAX_GATEWAY_SESSIONS:
                return False
            if self._sessions_by_ip.get(ip, 0) >= MAX_GATEWAY_SESSIONS_PER_IP:
                return False
            self._active_sessions += 1
            self._sessions_by_ip[ip] = self._sessions_by_ip.get(ip, 0) + 1
            return True

    def _release_session(self, address) -> None:
        ip = address[0]
        with self._sessions_lock:
            self._active_sessions -= 1
            remaining = self._sessions_by_ip[ip] - 1
            if remaining:
                self._sessions_by_ip[ip] = remaining
            else:
                del self._sessions_by_ip[ip]

    def _serve_client(self, client, address) -> None:
        try:
            self._handle_client(client, address)
        finally:
            self._release_session(address)

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
        self._ban_file_path = os.path.join(
            os.path.dirname(os.path.abspath(settings.ssh_gateway_host_key_path)),
            "ssh_gateway_bans.json",
        )
        self._load_bans()
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
            if self._is_ip_blocked(address[0]):
                client.close()
                continue
            if not self._reserve_session(address):
                client.close()
                continue
            try:
                threading.Thread(
                    target=self._serve_client,
                    args=(client, address),
                    daemon=True,
                    name=f"ssh-gateway-session-{address[0]}",
                ).start()
            except Exception:
                self._release_session(address)
                client.close()
                logger.exception("启动 SSH 网关会话失败")

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
                    upstream_command, sudo_password = _prepare_gateway_exec(
                        host,
                        server.auth_context.user,
                        request.exec_command or "",
                    )
                    upstream = open_exec(
                        upstream_command,
                        request_pty=request.pty_requested or bool(sudo_password),
                        term=request.pty_term,
                        width=request.pty_width,
                        height=request.pty_height,
                    )
                    if sudo_password:
                        upstream.sendall(f"{sudo_password}\n".encode("utf-8"))
                        sudo_password = None
                elif request.request_type == "shell":
                    open_shell = getattr(upstream_client, "open_shell", None)
                    if not open_shell:
                        raise RuntimeError("SSH 客户端不支持交互式 shell")
                    upstream = open_shell(
                        term=request.pty_term,
                        width=request.pty_width,
                        height=request.pty_height,
                    )
                    if host.credential.username != "root":
                        sudo_password = _gateway_sudo_password(
                            host, server.auth_context.user
                        )
                        if sudo_password and not _prime_interactive_sudo(
                            upstream, sudo_password
                        ):
                            logger.warning(
                                "SSH 网关 sudo 预认证失败: host=%s", host.name
                            )
                        sudo_password = None
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
        ip = address[0]
        server = GatewayServerInterface(
            on_auth_failure=lambda: self._record_auth_failure(ip),
            on_auth_success=lambda: self._clear_auth_failures(ip),
        )
        workers = []
        try:
            transport = paramiko.Transport(client_socket)
            transport.local_version = "SSH-2.0-frp-agent-gateway"
            transport.banner_timeout = HANDSHAKE_TIMEOUT_SECONDS
            transport.handshake_timeout = HANDSHAKE_TIMEOUT_SECONDS
            transport.add_server_key(self._host_key)
            transport.start_server(server=server)
            auth_deadline = time.monotonic() + AUTH_DEADLINE_SECONDS
            while transport.is_active() and not self._stop_event.is_set():
                if not server.auth_context and self._is_ip_blocked(ip):
                    raise PermissionError("SSH 网关来源已临时封禁")
                if not server.auth_context:
                    if server.failed_auth_attempts >= MAX_AUTH_FAILURES:
                        raise PermissionError("SSH 网关认证失败次数过多")
                    if time.monotonic() >= auth_deadline:
                        raise TimeoutError("SSH 网关认证超时")
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
