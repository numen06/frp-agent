"""SSH 客户端封装（便于测试替换）"""
from __future__ import annotations

import io
import logging
import base64
import hashlib
from dataclasses import dataclass
from typing import Optional, Protocol

import paramiko

logger = logging.getLogger(__name__)


@dataclass
class CommandResult:
    exit_code: int
    stdout: str
    stderr: str


class SSHClientProtocol(Protocol):
    def connect(self, host: str, port: int, username: str, timeout: float = 15.0) -> None: ...
    def exec_command(
        self, command: str, timeout: float = 30.0, stdin_data: Optional[str] = None
    ) -> CommandResult: ...
    def upload_file(self, local_path: str, remote_path: str) -> None: ...
    def close(self) -> None: ...


class ParamikoSSHClient:
    """基于 paramiko 的 SSH/SFTP 实现"""

    def __init__(
        self,
        password: Optional[str] = None,
        private_key: Optional[str] = None,
        passphrase: Optional[str] = None,
        expected_host_key: Optional[str] = None,
    ):
        self._password = password
        self._private_key = private_key
        self._passphrase = passphrase
        self._expected_host_key = expected_host_key
        self._client: Optional[paramiko.SSHClient] = None
        self._sftp: Optional[paramiko.SFTPClient] = None

    def connect(self, host: str, port: int, username: str, timeout: float = 15.0) -> None:
        client = paramiko.SSHClient()
        if self._expected_host_key:
            client.set_missing_host_key_policy(
                FingerprintPolicy(self._expected_host_key)
            )
        else:
            # 首次连接采用 TOFU；调用方应立即保存 get_server_fingerprint() 的结果。
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        pkey = None
        if self._private_key:
            key_data = self._private_key
            for key_cls in (
                paramiko.RSAKey,
                paramiko.ECDSAKey,
                paramiko.Ed25519Key,
            ):
                try:
                    pkey = key_cls.from_private_key(
                        io.StringIO(key_data),
                        password=self._passphrase or None,
                    )
                    break
                except Exception:
                    continue
            if pkey is None:
                raise ValueError("无法解析私钥")
        client.connect(
            hostname=host,
            port=port,
            username=username,
            password=self._password if not pkey else None,
            pkey=pkey,
            timeout=timeout,
            allow_agent=False,
            look_for_keys=False,
        )
        self._client = client
        try:
            self._sftp = client.open_sftp()
        except Exception:
            # 交互式跳板/命令执行不应因目标未启用 SFTP 而失败。
            logger.debug("目标 SSH 未启用 SFTP", exc_info=True)
            self._sftp = None

    def get_server_fingerprint(self) -> Optional[str]:
        if not self._client:
            return None
        transport = self._client.get_transport()
        if not transport:
            return None
        key = transport.get_remote_server_key()
        return format_host_key_fingerprint(key)

    def open_shell(
        self, term: str = "xterm-256color", width: int = 120, height: int = 40
    ) -> paramiko.Channel:
        if not self._client:
            raise RuntimeError("SSH 未连接")
        return self._client.invoke_shell(
            term=term, width=width, height=height
        )

    def open_exec_channel(
        self,
        command: str,
        *,
        request_pty: bool = False,
        term: str = "xterm-256color",
        width: int = 120,
        height: int = 40,
    ) -> paramiko.Channel:
        if not self._client:
            raise RuntimeError("SSH 未连接")
        transport = self._client.get_transport()
        if not transport:
            raise RuntimeError("SSH Transport 不可用")
        channel = transport.open_session()
        if request_pty:
            channel.get_pty(term=term, width=width, height=height)
        channel.exec_command(command)
        return channel

    def open_subsystem_channel(self, subsystem: str) -> paramiko.Channel:
        if not self._client:
            raise RuntimeError("SSH 未连接")
        if subsystem != "sftp":
            raise ValueError(f"不支持的 SSH 子系统: {subsystem}")
        transport = self._client.get_transport()
        if not transport:
            raise RuntimeError("SSH Transport 不可用")
        channel = transport.open_session()
        channel.invoke_subsystem(subsystem)
        return channel

    def exec_command(
        self, command: str, timeout: float = 30.0, stdin_data: Optional[str] = None
    ) -> CommandResult:
        if not self._client:
            raise RuntimeError("SSH 未连接")
        stdin, stdout, stderr = self._client.exec_command(command, timeout=timeout)
        if stdin_data is not None:
            stdin.write(stdin_data)
            stdin.flush()
            stdin.channel.shutdown_write()
        exit_code = stdout.channel.recv_exit_status()
        out = stdout.read().decode("utf-8", errors="replace").strip()
        err = stderr.read().decode("utf-8", errors="replace").strip()
        return CommandResult(exit_code=exit_code, stdout=out, stderr=err)

    def upload_file(self, local_path: str, remote_path: str) -> None:
        if not self._sftp:
            raise RuntimeError("SFTP 未就绪")
        self._sftp.put(local_path, remote_path)

    def close(self) -> None:
        if self._sftp:
            try:
                self._sftp.close()
            except Exception:
                pass
            self._sftp = None
        if self._client:
            try:
                self._client.close()
            except Exception:
                pass
            self._client = None


def build_ssh_client(
    auth_type: str,
    password: Optional[str],
    private_key: Optional[str],
    passphrase: Optional[str],
    expected_host_key: Optional[str] = None,
) -> SSHClientProtocol:
    if auth_type == "password":
        return ParamikoSSHClient(
            password=password, expected_host_key=expected_host_key
        )
    if auth_type == "private_key":
        return ParamikoSSHClient(
            private_key=private_key,
            passphrase=passphrase,
            expected_host_key=expected_host_key,
        )
    raise ValueError(f"不支持的认证类型: {auth_type}")


def format_host_key_fingerprint(key: paramiko.PKey) -> str:
    digest = hashlib.sha256(key.asbytes()).digest()
    return "SHA256:" + base64.b64encode(digest).decode("ascii").rstrip("=")


class FingerprintPolicy(paramiko.MissingHostKeyPolicy):
    """只接受与已登记 SHA256 指纹完全一致的主机密钥。"""

    def __init__(self, expected: str):
        self.expected = expected.strip()

    def missing_host_key(self, client, hostname, key):
        actual = format_host_key_fingerprint(key)
        if not secrets_compare(actual, self.expected):
            raise paramiko.SSHException(
                f"SSH 主机指纹不匹配：期望 {self.expected}，实际 {actual}"
            )
        client.get_host_keys().add(hostname, key.get_name(), key)


def secrets_compare(left: str, right: str) -> bool:
    import secrets

    return secrets.compare_digest(left.encode("utf-8"), right.encode("utf-8"))
