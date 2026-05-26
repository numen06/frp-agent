"""SSH frpc 客户端扫描与升级（主机端脚本模式）"""
from __future__ import annotations

import json
import logging
import os
import re
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.orm import Session, joinedload

from app.models.client_upgrade_job import ClientUpgradeJob
from app.models.frp_package import FrpPackage
from app.models.proxy import Proxy
from app.models.proxy_ssh_state import ProxySshState
from app.models.ssh_credential import SshCredential
from app.services.credential_encryption import decrypt_secret
from app.services.frp_version_util import (
    is_upgradeable,
    normalize_version_display,
    parse_version,
    version_sort_key,
)
from app.services.package_extract import cleanup_extract_dir, extract_frpc_binary
from app.services.ssh_candidate import is_ssh_candidate, ssh_target_host, ssh_target_port
from app.services.ssh_client import SSHClientProtocol, build_ssh_client

logger = logging.getLogger(__name__)

ARCH_MAP = {
    "x86_64": "linux_amd64",
    "amd64": "linux_amd64",
    "aarch64": "linux_arm64",
    "arm64": "linux_arm64",
    "armv7l": "linux_arm",
}

GROUP_SCAN_CONCURRENCY = 3


def map_linux_arch(uname_m: str) -> Optional[str]:
    return ARCH_MAP.get((uname_m or "").strip().lower())


def get_credential_secrets(cred: SshCredential) -> Tuple[str, Optional[str], Optional[str], Optional[str]]:
    return (
        cred.auth_type,
        decrypt_secret(cred.password_encrypted),
        decrypt_secret(cred.private_key_encrypted),
        decrypt_secret(cred.passphrase_encrypted),
    )


def select_latest_package(db: Session, platform: str) -> Optional[FrpPackage]:
    packages = (
        db.query(FrpPackage)
        .filter(FrpPackage.platform == platform, FrpPackage.is_active == True)
        .all()
    )
    if not packages:
        return None
    return max(packages, key=lambda p: version_sort_key(p.version or ""))


def get_or_create_ssh_state(db: Session, proxy_id: int) -> ProxySshState:
    state = db.query(ProxySshState).filter(ProxySshState.proxy_id == proxy_id).first()
    if not state:
        state = ProxySshState(proxy_id=proxy_id)
        db.add(state)
    return state


def state_to_dict(state: ProxySshState, proxy: Optional[Proxy] = None) -> dict:
    result = {
        "proxy_id": state.proxy_id,
        "credential_id": state.credential_id,
        "is_ssh_candidate": state.is_ssh_candidate,
        "reachable": state.reachable,
        "platform": state.platform,
        "install_path": state.install_path,
        "frpc_bin_path": state.frpc_bin_path,
        "config_path": state.config_path,
        "config_format": state.config_format,
        "has_ini": state.has_ini,
        "has_toml": state.has_toml,
        "service_name": state.service_name,
        "current_version": state.current_version,
        "target_version": state.target_version,
        "target_package_id": state.target_package_id,
        "upgradeable": state.upgradeable,
        "rollback_capable": state.rollback_capable,
        "status": state.status,
        "message": state.message,
        "last_scanned_at": state.last_scanned_at,
        "last_upgraded_at": state.last_upgraded_at,
        "proxy_name": proxy.name if proxy else None,
    }
    if proxy and proxy.frps_server:
        result["ssh_target"] = f"{proxy.frps_server.server_addr}:{proxy.remote_port}"
    return result


def _run_cmd(ssh: SSHClientProtocol, cmd: str, timeout: float = 30.0):
    return ssh.exec_command(cmd, timeout=timeout)


def _parse_systemd_exec_start(stdout: str) -> Dict[str, Optional[str]]:
    """解析 systemd ExecStart 获取 frpc 二进制路径和 -c 配置路径。"""
    result = {"bin_path": None, "config_path": None}
    for line in stdout.splitlines():
        line = line.strip()
        if line.startswith("ExecStart="):
            exec_part = line[len("ExecStart="):]
            # 解析命令行参数
            parts = exec_part.split()
            if parts:
                result["bin_path"] = parts[0]
                # 查找 -c 参数
                for i, part in enumerate(parts):
                    if part == "-c" and i + 1 < len(parts):
                        result["config_path"] = parts[i + 1]
                        break
            break
    return result


def _detect_config_files(
    ssh: SSHClientProtocol,
    install_path: str,
    service_name: str = "frpc",
    systemd_config_path: Optional[str] = None,
) -> Dict[str, Any]:
    """检测 frpc 配置文件位置和格式。"""
    result = {
        "config_path": None,
        "config_format": "unknown",
        "has_ini": False,
        "has_toml": False,
    }

    candidate_paths = []

    # 1. systemd ExecStart -c 参数优先
    if systemd_config_path:
        candidate_paths.append(systemd_config_path)

    # 2. 安装路径下的配置文件
    candidate_paths.extend([
        f"{install_path}/frpc.toml",
        f"{install_path}/frpc.ini",
        "/etc/frp/frpc.toml",
        "/etc/frp/frpc.ini",
    ])

    toml_exists = False
    ini_exists = False
    first_existing = None

    for path in candidate_paths:
        check = _run_cmd(ssh, f"test -f {path} && echo exists || echo not_found")
        if "exists" in check.stdout:
            if path.endswith(".toml"):
                toml_exists = True
            elif path.endswith(".ini"):
                ini_exists = True
            if first_existing is None:
                first_existing = path

    result["has_ini"] = ini_exists
    result["has_toml"] = toml_exists

    if first_existing:
        result["config_path"] = first_existing
        if first_existing.endswith(".toml"):
            result["config_format"] = "toml"
        elif first_existing.endswith(".ini"):
            result["config_format"] = "ini"

    return result


def _detect_frpc_binary(
    ssh: SSHClientProtocol,
    install_path: str,
    service_name: str = "frpc",
) -> Dict[str, Any]:
    """检测 frpc 二进制路径。"""
    result = {"frpc_bin_path": None, "install_path": install_path}

    # 从 systemd 服务获取
    svc_cat = _run_cmd(ssh, f"systemctl cat {service_name} 2>/dev/null || true")
    if svc_cat.exit_code == 0 and svc_cat.stdout:
        parsed = _parse_systemd_exec_start(svc_cat.stdout)
        if parsed["bin_path"]:
            result["frpc_bin_path"] = parsed["bin_path"]
            # 从二进制路径推导安装路径
            bin_dir = os.path.dirname(parsed["bin_path"])
            if bin_dir and bin_dir != "/usr/bin" and bin_dir != "/bin":
                result["install_path"] = bin_dir

    # 如果没找到，检查安装路径
    if not result["frpc_bin_path"]:
        candidates = [
            f"{install_path}/frpc",
            "/usr/local/bin/frpc",
            "/usr/bin/frpc",
        ]
        for path in candidates:
            check = _run_cmd(ssh, f"test -x {path} && echo exists || echo not_found")
            if "exists" in check.stdout:
                result["frpc_bin_path"] = path
                break

    # command -v
    if not result["frpc_bin_path"]:
        which = _run_cmd(ssh, "command -v frpc 2>/dev/null || true")
        if which.stdout.strip():
            result["frpc_bin_path"] = which.stdout.strip()

    return result


def scan_proxy_remote(
    ssh: SSHClientProtocol,
    install_path: str,
    service_name: str = "frpc",
) -> Dict[str, Any]:
    """在已连接的 SSH 上收集扫描信息（增强版）。"""
    install_path = install_path.rstrip("/") or "/opt/frp"
    info: Dict[str, Any] = {
        "install_path": install_path,
        "service_name": service_name,
    }

    # OS 和架构
    os_result = _run_cmd(ssh, "uname -s")
    arch_result = _run_cmd(ssh, "uname -m")
    info["os_name"] = os_result.stdout.strip()
    info["arch"] = arch_result.stdout.strip()

    if info["os_name"].lower() != "linux":
        info["status"] = "unsupported_platform"
        info["message"] = f"不支持的操作系统: {info['os_name']}"
        return info

    platform = map_linux_arch(info["arch"])
    if not platform:
        info["status"] = "unsupported_platform"
        info["message"] = f"不支持的架构: {info['arch']}"
        return info
    info["platform"] = platform

    # 权限检测
    uid_result = _run_cmd(ssh, "id -u")
    info["uid"] = uid_result.stdout.strip()
    info["is_root"] = info["uid"] == "0"

    sudo_result = _run_cmd(ssh, "sudo -n true 2>/dev/null; echo $?")
    info["has_passwordless_sudo"] = sudo_result.stdout.strip().endswith("0")

    # 检测 frpc 二进制
    bin_info = _detect_frpc_binary(ssh, install_path, service_name)
    info["frpc_bin_path"] = bin_info["frpc_bin_path"]
    info["install_path"] = bin_info["install_path"]
    actual_install_path = bin_info["install_path"] or install_path

    # 检测配置文件
    # 先获取 systemd 信息
    systemd_config_path = None
    svc_cat = _run_cmd(ssh, f"systemctl cat {service_name} 2>/dev/null || true")
    if svc_cat.exit_code == 0 and svc_cat.stdout:
        parsed = _parse_systemd_exec_start(svc_cat.stdout)
        systemd_config_path = parsed.get("config_path")

    config_info = _detect_config_files(
        ssh, actual_install_path, service_name, systemd_config_path
    )
    info["config_path"] = config_info["config_path"]
    info["config_format"] = config_info["config_format"]
    info["has_ini"] = config_info["has_ini"]
    info["has_toml"] = config_info["has_toml"]

    # 版本检测
    frpc_bin = info["frpc_bin_path"] or f"{actual_install_path}/frpc"
    ver_result = _run_cmd(ssh, f"{frpc_bin} --version 2>&1 || true")
    info["current_version_raw"] = ver_result.stdout or ver_result.stderr
    info["current_version"] = normalize_version_display(info["current_version_raw"])

    # 服务状态
    svc_active = _run_cmd(ssh, f"systemctl is-active {service_name} 2>/dev/null || echo inactive")
    info["service_active"] = svc_active.stdout.strip() == "active"

    svc_enabled = _run_cmd(ssh, f"systemctl is-enabled {service_name} 2>/dev/null || echo disabled")
    info["service_enabled"] = svc_enabled.stdout.strip() == "enabled"

    # 写权限检测
    writable = _run_cmd(
        ssh,
        f"test -w {actual_install_path} 2>/dev/null && echo ok || "
        f"(sudo -n test -w {actual_install_path} 2>/dev/null && echo ok_sudo || echo denied)",
    )
    info["writable"] = "ok" in writable.stdout or "ok_sudo" in writable.stdout

    # 回滚能力：需要写权限和备份空间
    info["rollback_capable"] = info["writable"] and (
        info["is_root"] or info["has_passwordless_sudo"]
    )

    if not info["writable"]:
        info["status"] = "permission_denied"
        info["message"] = f"对 {actual_install_path} 无写权限且无法 sudo"
        return info

    info["status"] = "reachable"
    info["message"] = "扫描成功"
    return info


def finalize_scan_state(
    db: Session,
    state: ProxySshState,
    proxy: Proxy,
    remote_info: Dict[str, Any],
    credential_id: int,
    install_path: str,
) -> ProxySshState:
    now = datetime.utcnow()
    state.credential_id = credential_id
    state.install_path = remote_info.get("install_path") or install_path
    state.is_ssh_candidate = is_ssh_candidate(proxy)
    state.last_scanned_at = now
    state.reachable = remote_info.get("status") == "reachable" or remote_info.get("status") in (
        "latest",
        "upgradeable",
        "no_package",
    )

    status = remote_info.get("status", "unknown")
    state.platform = remote_info.get("platform")
    state.frpc_bin_path = remote_info.get("frpc_bin_path")
    state.config_path = remote_info.get("config_path")
    state.config_format = remote_info.get("config_format")
    state.has_ini = remote_info.get("has_ini", False)
    state.has_toml = remote_info.get("has_toml", False)
    state.service_name = remote_info.get("service_name", "frpc")
    state.current_version = remote_info.get("current_version")
    state.rollback_capable = remote_info.get("rollback_capable", False)
    state.message = remote_info.get("message")

    if status == "reachable":
        platform = remote_info.get("platform")
        pkg = select_latest_package(db, platform) if platform else None
        if not pkg:
            state.status = "no_package"
            state.upgradeable = False
            state.target_version = None
            state.target_package_id = None
            state.message = f"未找到平台 {platform} 的可用安装包"
        else:
            state.target_version = pkg.version
            state.target_package_id = pkg.id
            current = state.current_version
            if parse_version(current) is None and current:
                state.status = "latest"
                state.upgradeable = False
                state.message = "无法解析当前版本，需手动确认后升级"
            elif is_upgradeable(current, pkg.version):
                state.status = "upgradeable"
                state.upgradeable = True
                state.message = f"可升级: {current or '未知'} -> {pkg.version}"
            else:
                state.status = "latest"
                state.upgradeable = False
                state.message = "已是最新版本"
    else:
        state.status = status
        state.upgradeable = False
        if status not in ("permission_denied", "unsupported_platform"):
            state.reachable = status == "reachable"

    db.commit()
    db.refresh(state)
    return state


def scan_single_proxy(
    db: Session,
    proxy: Proxy,
    credential: SshCredential,
    install_path: str = "/opt/frp",
    ssh_factory=None,
) -> ProxySshState:
    state = get_or_create_ssh_state(db, proxy.id)

    if not is_ssh_candidate(proxy):
        state.is_ssh_candidate = False
        state.status = "not_ssh"
        state.upgradeable = False
        state.message = "该代理不符合 SSH 升级条件（需 tcp/22/有远程端口/在线）"
        state.last_scanned_at = datetime.utcnow()
        db.commit()
        db.refresh(state)
        return state

    state.is_ssh_candidate = True
    auth_type, password, private_key, passphrase = get_credential_secrets(credential)
    host = ssh_target_host(proxy)
    port = ssh_target_port(proxy)

    ssh = ssh_factory(credential) if ssh_factory else _connect_credential(
        auth_type, password, private_key, passphrase
    )
    try:
        if ssh_factory is None:
            ssh.connect(host, port, credential.username)
        remote_info = scan_proxy_remote(ssh, install_path)
    except Exception as e:
        err_msg = str(e)
        if "Authentication" in err_msg or "authentication" in err_msg:
            state.status = "auth_failed"
            state.message = "SSH 认证失败"
        else:
            state.status = "unreachable"
            state.message = f"无法连接 SSH: {err_msg}"
        state.reachable = False
        state.upgradeable = False
        state.last_scanned_at = datetime.utcnow()
        db.commit()
        db.refresh(state)
        return state
    finally:
        ssh.close()

    return finalize_scan_state(db, state, proxy, remote_info, credential.id, install_path)


def _connect_credential(auth_type, password, private_key, passphrase) -> SSHClientProtocol:
    return build_ssh_client(auth_type, password, private_key, passphrase)


# ── 主机端升级脚本生成 ──────────────────────────────────────────────

def generate_upgrade_script(
    job_id: int,
    frpc_bin: str,
    config_path: Optional[str],
    install_path: str,
    service_name: str,
    new_frpc_path: str,
    expected_version: str,
    verify_mode: str,
    verify_url: Optional[str] = None,
    verify_proxy_name: Optional[str] = None,
    verify_attempts: int = 18,
    verify_interval: int = 5,
    has_ini: bool = False,
    has_toml: bool = False,
) -> str:
    """生成主机端执行的升级脚本。"""
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    backup_dir = f"{install_path}/.frp-agent-backups/{timestamp}"
    result_file = f"/tmp/frp-agent-upgrade/{job_id}/result.json"

    config_backup_section = ""
    if config_path:
        config_basename = os.path.basename(config_path)
        config_backup_section = f'''
CONFIG_PATH="{config_path}"
CONFIG_BASENAME="{config_basename}"
'''

    # 配置备份命令
    config_backup_cmd = ""
    if config_path:
        config_backup_cmd = f'''
if [ -f "$CONFIG_PATH" ]; then
    cp -f "$CONFIG_PATH" "$BACKUP_DIR/$CONFIG_BASENAME"
    echo "Backed up config: $CONFIG_PATH"
fi'''

    # 额外备份 INI/TOML
    extra_backup_cmd = ""
    if has_ini:
        extra_backup_cmd += f'''
if [ -f "{install_path}/frpc.ini" ]; then
    cp -f "{install_path}/frpc.ini" "$BACKUP_DIR/frpc.ini"
    echo "Backed up frpc.ini"
fi'''
    if has_toml:
        extra_backup_cmd += f'''
if [ -f "{install_path}/frpc.toml" ]; then
    cp -f "{install_path}/frpc.toml" "$BACKUP_DIR/frpc.toml"
    echo "Backed up frpc.toml"
fi'''

    # 配置恢复命令
    config_restore_cmd = ""
    if config_path:
        config_restore_cmd = f'''
if [ -f "$BACKUP_DIR/$CONFIG_BASENAME" ]; then
    cp -f "$BACKUP_DIR/$CONFIG_BASENAME" "$CONFIG_PATH"
    echo "Restored config: $CONFIG_PATH"
fi'''

    # 额外恢复
    extra_restore_cmd = ""
    if has_ini:
        extra_restore_cmd += f'''
if [ -f "$BACKUP_DIR/frpc.ini" ]; then
    cp -f "$BACKUP_DIR/frpc.ini" "{install_path}/frpc.ini"
    echo "Restored frpc.ini"
fi'''
    if has_toml:
        extra_restore_cmd += f'''
if [ -f "$BACKUP_DIR/frpc.toml" ]; then
    cp -f "$BACKUP_DIR/frpc.toml" "{install_path}/frpc.toml"
    echo "Restored frpc.toml"
fi'''

    # 验证模式
    verify_section = ""
    if verify_mode == "agent_callback" and verify_url:
        verify_section = f'''
echo "Verifying via frp-agent callback..."
VERIFY_OK=false
for i in $(seq 1 {verify_attempts}); do
    sleep {verify_interval}
    RESP=$(curl -s "{verify_url}" 2>/dev/null || echo '{{"ok":false}}')
    OK=$(echo "$RESP" | grep -o '"ok"[[:space:]]*:[[:space:]]*true' || true)
    if [ -n "$OK" ]; then
        VERIFY_OK=true
        echo "Verification passed (attempt $i)"
        break
    fi
    echo "Verification attempt $i failed: $RESP"
done
if [ "$VERIFY_OK" != "true" ]; then
    echo "Verification failed after {verify_attempts} attempts"
    ROLLBACK_REASON="verification_failed"
fi'''
    elif verify_mode == "skip":
        verify_section = '''
echo "Verification skipped"
VERIFY_OK=true'''
    else:
        verify_section = '''
echo "No remote verification configured"
VERIFY_OK=true'''

    # 回滚函数
    rollback_func = f'''
rollback() {{
    echo "Rolling back..."
    systemctl stop {service_name} 2>/dev/null || true
    if [ -f "$BACKUP_DIR/frpc" ]; then
        cp -f "$BACKUP_DIR/frpc" "$FRPC_BIN"
        chmod 755 "$FRPC_BIN"
        echo "Restored binary: $FRPC_BIN"
    fi
    {config_restore_cmd}
    {extra_restore_cmd}
    systemctl start {service_name} 2>/dev/null || systemctl restart {service_name} 2>/dev/null || true
    echo "Rollback completed"
}}'''

    script = f'''#!/bin/bash
set -e

# SSH frpc Client Upgrade Script
# Generated by frp-agent
# Job ID: {job_id}

JOB_ID="{job_id}"
FRPC_BIN="{frpc_bin}"
INSTALL_PATH="{install_path}"
SERVICE_NAME="{service_name}"
NEW_FRPC_PATH="{new_frpc_path}"
EXPECTED_VERSION="{expected_version}"
BACKUP_DIR="{backup_dir}"
RESULT_FILE="{result_file}"
{config_backup_section}

ROLLBACK_REASON=""

{rollback_func}

write_result() {{
    local success="$1"
    local rolled_back="$2"
    local old_ver="$3"
    local final_ver="$4"
    local msg="$5"
    cat > "$RESULT_FILE" << EOF
{{
  "success": $success,
  "rolled_back": $rolled_back,
  "old_version": "$old_ver",
  "target_version": "$EXPECTED_VERSION",
  "final_version": "$final_ver",
  "message": "$msg",
  "backup_dir": "$BACKUP_DIR"
}}
EOF
}}

# 1. Validate
if [ ! -f "$FRPC_BIN" ]; then
    echo "Error: Old binary not found: $FRPC_BIN"
    write_result false false "" "" "Old binary not found: $FRPC_BIN"
    exit 1
fi

if [ ! -f "$NEW_FRPC_PATH" ]; then
    echo "Error: New binary not found: $NEW_FRPC_PATH"
    write_result false false "" "" "New binary not found: $NEW_FRPC_PATH"
    exit 1
fi

OLD_VERSION=$($FRPC_BIN --version 2>&1 | grep -oE '[0-9]+\\.[0-9]+\\.[0-9]+' || echo "unknown")

# 2. Create backup directory
mkdir -p "$BACKUP_DIR"
mkdir -p "$(dirname $RESULT_FILE)"

# 3. Backup
echo "Creating backup in $BACKUP_DIR..."
cp -f "$FRPC_BIN" "$BACKUP_DIR/frpc"
{config_backup_cmd}
{extra_backup_cmd}

# Write metadata
cat > "$BACKUP_DIR/metadata.json" << EOF
{{
  "timestamp": "{timestamp}",
  "job_id": {job_id},
  "old_binary": "$FRPC_BIN",
  "old_version": "$OLD_VERSION",
  "target_version": "$EXPECTED_VERSION",
  "config_path": "{config_path or ""}",
  "service_name": "$SERVICE_NAME"
}}
EOF
echo "Backup metadata written"

# 4. Stop service
echo "Stopping service $SERVICE_NAME..."
systemctl stop $SERVICE_NAME 2>/dev/null || true

# 5. Replace binary
echo "Replacing binary..."
cp -f "$NEW_FRPC_PATH" "$FRPC_BIN"
chmod 755 "$FRPC_BIN"

# 6. Start service
echo "Starting service $SERVICE_NAME..."
systemctl start $SERVICE_NAME 2>/dev/null || systemctl restart $SERVICE_NAME 2>/dev/null || true

# 7. Verify binary version
sleep 1
NEW_VERSION=$($FRPC_BIN --version 2>&1 | grep -oE '[0-9]+\\.[0-9]+\\.[0-9]+' || echo "unknown")
if [ "$NEW_VERSION" != "$EXPECTED_VERSION" ]; then
    echo "Version mismatch: expected $EXPECTED_VERSION, got $NEW_VERSION"
    ROLLBACK_REASON="version_mismatch"
fi

# 8. Verify service active
SERVICE_ACTIVE=$(systemctl is-active $SERVICE_NAME 2>/dev/null || echo "inactive")
if [ "$SERVICE_ACTIVE" != "active" ]; then
    echo "Service not active: $SERVICE_ACTIVE"
    ROLLBACK_REASON="service_not_active"
fi

# 9. Remote verification
if [ -z "$ROLLBACK_REASON" ]; then
    {verify_section}
fi

# 10. Handle result
if [ -n "$ROLLBACK_REASON" ]; then
    echo "Upgrade failed: $ROLLBACK_REASON"
    rollback
    write_result false true "$OLD_VERSION" "$OLD_VERSION" "Upgrade failed ($ROLLBACK_REASON); rolled back to $OLD_VERSION"
else
    echo "Upgrade successful: $OLD_VERSION -> $NEW_VERSION"
    write_result true false "$OLD_VERSION" "$NEW_VERSION" "Upgrade successful: $OLD_VERSION -> $NEW_VERSION"
fi

echo "Result written to $RESULT_FILE"
'''

    return script


def upgrade_single_proxy(
    db: Session,
    proxy: Proxy,
    credential: SshCredential,
    install_path: str = "/opt/frp",
    verify_mode: str = "agent_callback",
    verify_attempts: int = 18,
    verify_interval: int = 5,
    verify_url_base: Optional[str] = None,
    auto_scan: bool = True,
    ssh_factory=None,
) -> Dict[str, Any]:
    """使用主机端脚本升级单个代理。"""
    state = get_or_create_ssh_state(db, proxy.id)

    if auto_scan or state.status not in ("upgradeable",):
        state = scan_single_proxy(db, proxy, credential, install_path, ssh_factory=ssh_factory)

    if state.status != "upgradeable" or not state.target_package_id:
        return {
            "success": False,
            "proxy_id": proxy.id,
            "status": state.status,
            "message": state.message or "当前不可升级",
        }

    package = db.query(FrpPackage).filter(FrpPackage.id == state.target_package_id).first()
    if not package:
        state.status = "no_package"
        state.message = "目标安装包不存在"
        db.commit()
        return {"success": False, "proxy_id": proxy.id, "status": state.status, "message": state.message}

    # 提取 frpc 二进制
    local_frpc = None
    try:
        local_frpc = extract_frpc_binary(package)
    except Exception as e:
        return {"success": False, "proxy_id": proxy.id, "status": "upgrade_failed", "message": str(e)}

    auth_type, password, private_key, passphrase = get_credential_secrets(credential)
    host = ssh_target_host(proxy)
    port = ssh_target_port(proxy)

    actual_install_path = (state.install_path or install_path).rstrip("/")
    frpc_bin = state.frpc_bin_path or f"{actual_install_path}/frpc"
    service_name = state.service_name or "frpc"

    # 生成 job_id
    job_ts = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    job_id = int(job_ts) if len(job_ts) < 10 else hash(job_ts) % 1000000000
    remote_tmp_dir = f"/tmp/frp-agent-upgrade/{job_id}"
    remote_frpc = f"{remote_tmp_dir}/frpc.new"
    remote_script = f"{remote_tmp_dir}/upgrade.sh"
    remote_result = f"{remote_tmp_dir}/result.json"

    # 构建验证 URL
    verify_url = None
    if verify_mode == "agent_callback" and verify_url_base:
        verify_url = f"{verify_url_base}/api/proxies/{proxy.id}/ssh-upgrade/verify?expected_version={package.version}"

    ssh = ssh_factory(credential) if ssh_factory else _connect_credential(
        auth_type, password, private_key, passphrase
    )

    try:
        if ssh_factory is None:
            ssh.connect(host, port, credential.username)

        # 创建远程目录
        _run_cmd(ssh, f"mkdir -p {remote_tmp_dir}")

        # 上传新二进制
        ssh.upload_file(local_frpc, remote_frpc)

        # 生成升级脚本
        script = generate_upgrade_script(
            job_id=job_id,
            frpc_bin=frpc_bin,
            config_path=state.config_path,
            install_path=actual_install_path,
            service_name=service_name,
            new_frpc_path=remote_frpc,
            expected_version=package.version,
            verify_mode=verify_mode,
            verify_url=verify_url,
            verify_proxy_name=proxy.name,
            verify_attempts=verify_attempts,
            verify_interval=verify_interval,
            has_ini=state.has_ini,
            has_toml=state.has_toml,
        )

        # 写入脚本到本地临时文件并上传
        with tempfile.NamedTemporaryFile(mode='w', suffix='.sh', delete=False) as f:
            f.write(script)
            script_path = f.name

        try:
            ssh.upload_file(script_path, remote_script)
        finally:
            os.unlink(script_path)

        # 执行脚本
        use_sudo = not _run_cmd(ssh, f"test -w {actual_install_path} && echo yes || echo no").stdout.strip().endswith("yes")
        sudo_prefix = "sudo -n " if use_sudo else ""
        exec_result = _run_cmd(ssh, f"{sudo_prefix}bash {remote_script}", timeout=300.0)

        # 读取结果
        result_json_raw = _run_cmd(ssh, f"cat {remote_result} 2>/dev/null || echo '{{}}'").stdout
        try:
            result_json = json.loads(result_json_raw)
        except json.JSONDecodeError:
            result_json = {
                "success": False,
                "rolled_back": False,
                "message": "无法解析脚本结果",
                "stdout": exec_result.stdout[:500] if exec_result.stdout else "",
                "stderr": exec_result.stderr[:500] if exec_result.stderr else "",
            }

        # 更新状态
        if result_json.get("success"):
            state.status = "upgraded"
            state.upgradeable = False
            state.current_version = result_json.get("final_version") or package.version
            state.last_upgraded_at = datetime.utcnow()
            state.message = result_json.get("message", "升级成功")
        elif result_json.get("rolled_back"):
            state.status = "rolled_back"
            state.upgradeable = True  # 仍然可升级
            state.message = result_json.get("message", "升级失败已回退")
        else:
            state.status = "upgrade_failed"
            state.message = result_json.get("message", "升级失败")

        db.commit()

        return {
            "success": result_json.get("success", False),
            "proxy_id": proxy.id,
            "status": state.status,
            "message": state.message,
            "rolled_back": result_json.get("rolled_back", False),
            "current_version": state.current_version,
            "backup_dir": result_json.get("backup_dir"),
        }

    except Exception as e:
        logger.exception("升级失败 proxy_id=%s", proxy.id)
        state.status = "upgrade_failed"
        state.message = f"升级异常: {e}"
        db.commit()
        return {
            "success": False,
            "proxy_id": proxy.id,
            "status": "upgrade_failed",
            "message": str(e),
        }
    finally:
        ssh.close()
        if local_frpc:
            cleanup_extract_dir(local_frpc)


def _load_proxy_with_server(db: Session, proxy_id: int) -> Optional[Proxy]:
    return (
        db.query(Proxy)
        .options(joinedload(Proxy.frps_server))
        .filter(Proxy.id == proxy_id)
        .first()
    )


def _group_ssh_candidates(
    db: Session, frps_server_id: int, group_name: str
) -> List[Proxy]:
    proxies = (
        db.query(Proxy)
        .options(joinedload(Proxy.frps_server))
        .filter(
            Proxy.frps_server_id == frps_server_id,
            Proxy.group_name == group_name,
        )
        .all()
    )
    return [p for p in proxies if is_ssh_candidate(p)]


def create_job(
    db: Session,
    job_type: str,
    scope_type: str,
    credential_id: int,
    frps_server_id: Optional[int] = None,
    group_name: Optional[str] = None,
    proxy_id: Optional[int] = None,
) -> ClientUpgradeJob:
    job = ClientUpgradeJob(
        job_type=job_type,
        scope_type=scope_type,
        frps_server_id=frps_server_id,
        group_name=group_name,
        proxy_id=proxy_id,
        credential_id=credential_id,
        status="running",
        started_at=datetime.utcnow(),
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def finish_job(
    db: Session,
    job: ClientUpgradeJob,
    results: List[dict],
    success_count: int,
    failed_count: int,
    skipped_count: int,
):
    total = len(results)
    job.total_count = total
    job.success_count = success_count
    job.failed_count = failed_count
    job.skipped_count = skipped_count
    job.result_json = json.dumps(results, ensure_ascii=False)
    if failed_count == 0 and success_count > 0:
        job.status = "success"
    elif success_count > 0:
        job.status = "partial_success"
    elif total == 0:
        job.status = "success"
        job.summary = "无 SSH 候选代理"
    else:
        job.status = "failed"
    job.summary = f"共 {total} 项，成功 {success_count}，失败 {failed_count}，跳过 {skipped_count}"
    job.finished_at = datetime.utcnow()
    db.commit()
    db.refresh(job)


def scan_group(
    db: Session,
    frps_server_id: int,
    group_name: str,
    credential: SshCredential,
    install_path: str = "/opt/frp",
) -> ClientUpgradeJob:
    candidates = _group_ssh_candidates(db, frps_server_id, group_name)
    job = create_job(
        db, "scan", "group", credential.id, frps_server_id, group_name
    )
    results: List[dict] = []
    success = failed = skipped = 0

    def _scan_one(proxy: Proxy) -> dict:
        try:
            state = scan_single_proxy(db, proxy, credential, install_path)
            return {"proxy_id": proxy.id, "proxy_name": proxy.name, **state_to_dict(state, proxy)}
        except Exception as e:
            return {
                "proxy_id": proxy.id,
                "proxy_name": proxy.name,
                "status": "unreachable",
                "message": str(e),
                "upgradeable": False,
            }

    with ThreadPoolExecutor(max_workers=GROUP_SCAN_CONCURRENCY) as pool:
        futures = {pool.submit(_scan_one, p): p for p in candidates}
        for fut in as_completed(futures):
            r = fut.result()
            results.append(r)
            st = r.get("status")
            if st == "upgradeable" or st == "latest" or st == "reachable":
                success += 1
            elif st == "not_ssh":
                skipped += 1
            else:
                failed += 1

    finish_job(db, job, results, success, failed, skipped)
    return job


def upgrade_group(
    db: Session,
    frps_server_id: int,
    group_name: str,
    credential: SshCredential,
    install_path: str = "/opt/frp",
    proxy_ids: Optional[List[int]] = None,
    verify_mode: str = "agent_callback",
    verify_attempts: int = 18,
    verify_interval: int = 5,
    verify_url_base: Optional[str] = None,
) -> ClientUpgradeJob:
    candidates = _group_ssh_candidates(db, frps_server_id, group_name)
    explicit_ids = bool(proxy_ids)
    if proxy_ids:
        id_set = set(proxy_ids)
        candidates = [p for p in candidates if p.id in id_set]
    else:
        for p in list(candidates):
            state = db.query(ProxySshState).filter(ProxySshState.proxy_id == p.id).first()
            if state and state.upgradeable:
                continue
            scan_single_proxy(db, p, credential, install_path)
        candidates = [
            p
            for p in candidates
            if (
                st := db.query(ProxySshState)
                .filter(ProxySshState.proxy_id == p.id)
                .first()
            )
            and st.upgradeable
        ]

    job = create_job(
        db, "upgrade", "group", credential.id, frps_server_id, group_name
    )
    results: List[dict] = []
    success = failed = skipped = 0

    for proxy in candidates:
        if not explicit_ids:
            state = db.query(ProxySshState).filter(ProxySshState.proxy_id == proxy.id).first()
            if not state or not state.upgradeable:
                skipped += 1
                results.append({
                    "proxy_id": proxy.id,
                    "proxy_name": proxy.name,
                    "success": False,
                    "status": state.status if state else "unknown",
                    "message": "跳过：不可升级",
                })
                continue
        r = upgrade_single_proxy(
            db, proxy, credential, install_path,
            verify_mode=verify_mode,
            verify_attempts=verify_attempts,
            verify_interval=verify_interval,
            verify_url_base=verify_url_base,
            auto_scan=explicit_ids,
        )
        results.append({"proxy_name": proxy.name, **r})
        if r.get("success"):
            success += 1
        else:
            failed += 1

    finish_job(db, job, results, success, failed, skipped)
    return job
