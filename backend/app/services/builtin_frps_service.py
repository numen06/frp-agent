"""管理镜像预装的 frps 子进程；验证配置后应用，失败恢复原配置。"""
from collections import deque
import logging
import os
from pathlib import Path
import secrets
import shutil
import subprocess
import tempfile
import threading
import time
from datetime import datetime

import httpx

from app.config import get_settings
from app.models.builtin_frps import BuiltinFrpsConfig
from app.models.frps_server import FrpsServer
from app.models.proxy import Proxy
from app.schemas.builtin_frps import BuiltinFrpsUpdate
from app.services.credential_encryption import decrypt_secret, encrypt_secret
from app.schemas.builtin_frps import BuiltinFrpsRawUpdate
from app.services.builtin_frps_config import (
    render_config, validate_document, form_from_document, parse_document, allowed_ranges, revision,
)

logger = logging.getLogger(__name__)
CONFIG_FIELDS = tuple(key for key in BuiltinFrpsUpdate.model_fields if key != "auth_token" and hasattr(BuiltinFrpsConfig, key))
CREATE_FLAGS = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0


def get_builtin_config(db):
    config = db.get(BuiltinFrpsConfig, 1)
    if config is None:
        config = BuiltinFrpsConfig(id=1)
        db.add(config)
        db.commit()
        db.refresh(config)
    return config


def runtime_config(config):
    values = {**BuiltinFrpsUpdate().model_dump(), **{key: getattr(config, key) for key in CONFIG_FIELDS}}
    # Do not create encrypted secrets during the first-login prompt: the user may
    # still be changing the initial password used by the development key fallback.
    values["auth_token"] = decrypt_secret(config.token_encrypted) if config.token_encrypted else secrets.token_urlsafe(32)
    values["dashboard_password"] = decrypt_secret(config.dashboard_password_encrypted) if config.dashboard_password_encrypted else secrets.token_urlsafe(32)
    if not values["auth_token"] or not values["dashboard_password"]:
        raise ValueError("内置 FRP 凭据无法解密，请检查 SSH_CREDENTIAL_SECRET 配置")
    values["dashboard_username"] = "frp-agent"
    if config.raw_config_encrypted:
        content = decrypt_secret(config.raw_config_encrypted)
        if not content:
            raise ValueError("原始配置无法解密，请检查 SSH_CREDENTIAL_SECRET")
        values.update(validate_document(content, config.enabled, config.public_addr))
    return values


def render_frps_config(config):
    return render_config(config)


def validate_app_ports(config):
    settings = get_settings()
    reserved = {settings.app_port}
    for name in ("ssh_gateway", "docker_gateway", "rdp_gateway"):
        if getattr(settings, name + "_enabled"):
            reserved.add(getattr(settings, name + "_port"))
    requested = {config[key] for key in ("bind_port", "dashboard_port", "vhost_http_port", "vhost_https_port", "kcp_bind_port", "quic_bind_port")} - {0}
    ranges = allowed_ranges(parse_document(render_frps_config(config)))
    if reserved & requested or any(start <= port <= end for start, end in ranges for port in reserved):
        raise ValueError("FRP 端口或代理范围与本程序/主机网关端口冲突")


class BuiltinFrpsService:
    def __init__(self):
        self._lock = threading.RLock()
        self._stop_event = threading.Event()
        self._process = None
        self._monitor = None
        self._desired = None
        self._error = None
        self._logs = deque(maxlen=60)
        self._version = None

    @property
    def running(self):
        return self._process is not None and self._process.poll() is None

    def _binary(self):
        binary = shutil.which(get_settings().builtin_frps_binary)
        if not binary:
            raise ValueError("未找到内置 frps 程序；请使用包含 FRP 的新版镜像，或设置 BUILTIN_FRPS_BINARY")
        return binary

    def _config_path(self):
        directory = Path(get_settings().builtin_frps_dir).resolve()
        directory.mkdir(parents=True, exist_ok=True)
        return directory / "frps.toml"

    @staticmethod
    def _redact(message, config):
        for key in ("auth_token", "dashboard_password"):
            if config.get(key):
                message = message.replace(config[key], "[REDACTED]")
        return message

    def _write_config(self, config, verify=True, replace=True):
        path = self._config_path()
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", newline="", dir=path.parent, suffix=".toml", delete=False) as file:
            temporary = Path(file.name)
            os.chmod(temporary, 0o600)
            file.write(render_frps_config(config))
        try:
            if verify:
                result = subprocess.run([self._binary(), "verify", "-c", str(temporary)],
                                        capture_output=True, text=True, timeout=10, creationflags=CREATE_FLAGS)
                if result.returncode:
                    detail = self._redact((result.stderr or result.stdout or "未知错误")[-2000:], config)
                    raise ValueError(f"frps 配置校验失败：{detail}")
            if replace:
                os.replace(temporary, path)
        finally:
            temporary.unlink(missing_ok=True)

    def _read_logs(self, process, config):
        try:
            for line in process.stdout:
                line = self._redact(line.rstrip(), config)
                self._logs.append(line[-2000:])
                logger.info("内置 frps: %s", line)
        finally:
            process.stdout.close()

    def _start_process(self, config):
        process = subprocess.Popen([self._binary(), "-c", str(self._config_path())],
                                   stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                   text=True, encoding="utf-8", errors="replace", creationflags=CREATE_FLAGS)
        self._process = process
        threading.Thread(target=self._read_logs, args=(process, dict(config)), daemon=True,
                         name="builtin-frps-logs").start()
        deadline = time.monotonic() + 5
        with httpx.Client(timeout=0.5, trust_env=False) as client:
            while time.monotonic() < deadline and not self._stop_event.is_set():
                if process.poll() is not None:
                    raise ValueError(f"frps 启动失败（退出码 {process.returncode}），请检查端口是否被占用")
                try:
                    response = client.get(f'http://127.0.0.1:{config["dashboard_port"]}/api/serverinfo',
                                          auth=(config.get("dashboard_username", "frp-agent"), config["dashboard_password"]))
                    if response.status_code == 200:
                        self._version = response.json().get("version")
                        return
                except (httpx.HTTPError, ValueError):
                    pass
                self._stop_event.wait(0.1)
        raise ValueError("frps 管理接口未就绪，请检查监听端口和运行日志")

    def _stop_process(self):
        process = self._process
        if process is not None:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=3)
            self._process = None

    def _supervise(self):
        while not self._stop_event.wait(5):
            with self._lock:
                if self._desired and not self.running:
                    try:
                        self._stop_process()
                        self._write_config(self._desired)
                        self._start_process(self._desired)
                        self._error = None
                    except Exception as exc:
                        self._error = self._redact(str(exc), self._desired)
                        logger.error("内置 frps 重启失败: %s", self._error)
                        self._stop_process()

    def apply(self, db, data: BuiltinFrpsUpdate | BuiltinFrpsRawUpdate):
        with self._lock:
            config = get_builtin_config(db)
            previous = runtime_config(config)
            if isinstance(data, BuiltinFrpsRawUpdate):
                if data.revision and data.revision != revision(render_frps_config(previous)):
                    raise ValueError("配置已被其他操作更新，请重新读取后再修改，当前草稿未应用")
                candidate = validate_document(data.content, data.enabled, data.public_addr)
            else:
                candidate = {**previous, **data.model_dump(exclude={"auth_token"}, exclude_unset=True)}
                candidate.pop("_raw_exact", None)
                if data.auth_token:
                    candidate["auth_token"] = data.auth_token
                candidate = validate_document(render_frps_config(candidate), candidate["enabled"], candidate["public_addr"])
            self._stop_event.clear()
            old_text = self._config_path().read_text(encoding="utf-8") if self._config_path().exists() else None
            # Verify before interrupting an existing process.
            if candidate["enabled"] or isinstance(data, BuiltinFrpsRawUpdate):
                validate_app_ports(candidate)
                self._write_config(candidate)
            self._stop_process()
            try:
                if candidate["enabled"]:
                    self._start_process(candidate)
                for key in CONFIG_FIELDS:
                    setattr(config, key, candidate[key])
                config.token_encrypted = encrypt_secret(candidate["auth_token"])
                config.dashboard_password_encrypted = encrypt_secret(candidate["dashboard_password"])
                config.raw_config_encrypted = encrypt_secret(render_frps_config(candidate))
                config.onboarding_seen = True
                server = db.query(FrpsServer).filter(FrpsServer.is_builtin.is_(True)).first()
                if server is None and candidate["enabled"]:
                    server = FrpsServer(name="内置 FRP 服务", is_builtin=True)
                    db.add(server)
                if server is not None:
                    server.server_addr = candidate["public_addr"]
                    server.server_port = candidate["bind_port"]
                    server.api_base_url = f'http://127.0.0.1:{candidate["dashboard_port"]}/api'
                    server.auth_username = candidate["dashboard_username"]
                    server.auth_password = candidate["dashboard_password"]
                    server.auth_token = candidate["auth_token"]
                    server.is_active = candidate["enabled"]
                    server.server_version = self._version
                    server.last_test_status = "online" if candidate["enabled"] else "offline"
                    server.last_test_time = datetime.utcnow()
                    server.last_test_message = "内置 FRP 已启动" if candidate["enabled"] else "内置 FRP 已关闭"
                    if not candidate["enabled"]:
                        db.query(Proxy).filter(Proxy.frps_server_id == server.id).update(
                            {Proxy.status: "offline", Proxy.cur_conns: 0}, synchronize_session="fetch"
                        )
                db.commit()
                self._desired = candidate if candidate["enabled"] else None
                self._error = None
            except Exception as exc:
                db.rollback()
                self._stop_process()
                self._error = self._redact(str(exc), candidate)
                if old_text is not None:
                    self._config_path().write_text(old_text, encoding="utf-8")
                else:
                    self._config_path().unlink(missing_ok=True)
                if previous["enabled"]:
                    try:
                        self._start_process(previous)
                    except Exception:
                        logger.exception("内置 frps 原配置恢复失败")
                raise ValueError(self._error) from exc
            self._start_monitor()
            return self.status(db)

    def _start_monitor(self):
        if not self._monitor or not self._monitor.is_alive():
            self._monitor = threading.Thread(target=self._supervise, daemon=True, name="builtin-frps-monitor")
            self._monitor.start()

    def restore(self, db):
        config = db.get(BuiltinFrpsConfig, 1)
        if config and config.enabled:
            try:
                self.apply(db, BuiltinFrpsRawUpdate(enabled=True, public_addr=config.public_addr,
                                                   content=render_frps_config(runtime_config(config))))
            except Exception as exc:
                self._error = str(exc)
                logger.error("内置 frps 启动失败: %s", exc)
                try:
                    self._desired = runtime_config(config)
                    self._start_monitor()
                except ValueError:
                    pass

    def status(self, db):
        with self._lock:
            config = get_builtin_config(db)
            server = db.query(FrpsServer).filter(FrpsServer.is_builtin.is_(True)).first()
            public_values = {**BuiltinFrpsUpdate().model_dump(exclude={"auth_token"}),
                             **{key: getattr(config, key) for key in CONFIG_FIELDS}}
            if config.raw_config_encrypted:
                content = decrypt_secret(config.raw_config_encrypted)
                if content:
                    public_values.update({key: value for key, value in form_from_document(parse_document(content)).items() if key != "auth_token"})
            return {
                **public_values,
                "onboarding_seen": config.onboarding_seen,
                "has_auth_token": bool(config.token_encrypted),
                "available": bool(shutil.which(get_settings().builtin_frps_binary)),
                "running": self.running,
                "version": self._version,
                "server_id": server.id if server else None,
                "error": self._error,
                "logs": list(self._logs),
            }

    def raw_document(self, db, data=None):
        with self._lock:
            config = get_builtin_config(db)
            values = runtime_config(config)
            if not config.token_encrypted or not config.dashboard_password_encrypted:
                config.token_encrypted = encrypt_secret(values["auth_token"])
                config.dashboard_password_encrypted = encrypt_secret(values["dashboard_password"])
                db.commit()
            saved = render_frps_config(values)
            if data is not None:
                values.update(data.model_dump(exclude={"auth_token"}, exclude_unset=True))
                values.pop("_raw_exact", None)
                if data.auth_token:
                    values["auth_token"] = data.auth_token
            content = render_frps_config(values)
            return {"content": content, "revision": revision(saved), "changed": content != saved}

    def validate_raw(self, data):
        candidate = validate_document(data.content, data.enabled, data.public_addr)
        validate_app_ports(candidate)
        self._write_config(candidate, replace=False)
        return {"valid": True}

    def stop(self):
        self._stop_event.set()
        with self._lock:
            self._desired = None
            self._stop_process()
        if self._monitor:
            self._monitor.join(timeout=6)
            self._monitor = None


builtin_frps_service = BuiltinFrpsService()
