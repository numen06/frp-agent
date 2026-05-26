"""SSH 客户端封装（便于测试替换）"""
from __future__ import annotations

import io
import logging
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
    def exec_command(self, command: str, timeout: float = 30.0) -> CommandResult: ...
    def upload_file(self, local_path: str, remote_path: str) -> None: ...
    def close(self) -> None: ...


class ParamikoSSHClient:
    """基于 paramiko 的 SSH/SFTP 实现"""

    def __init__(
        self,
        password: Optional[str] = None,
        private_key: Optional[str] = None,
        passphrase: Optional[str] = None,
    ):
        self._password = password
        self._private_key = private_key
        self._passphrase = passphrase
        self._client: Optional[paramiko.SSHClient] = None
        self._sftp: Optional[paramiko.SFTPClient] = None

    def connect(self, host: str, port: int, username: str, timeout: float = 15.0) -> None:
        client = paramiko.SSHClient()
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
        self._sftp = client.open_sftp()

    def exec_command(self, command: str, timeout: float = 30.0) -> CommandResult:
        if not self._client:
            raise RuntimeError("SSH 未连接")
        stdin, stdout, stderr = self._client.exec_command(command, timeout=timeout)
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
) -> SSHClientProtocol:
    if auth_type == "password":
        return ParamikoSSHClient(password=password)
    if auth_type == "private_key":
        return ParamikoSSHClient(private_key=private_key, passphrase=passphrase)
    raise ValueError(f"不支持的认证类型: {auth_type}")
