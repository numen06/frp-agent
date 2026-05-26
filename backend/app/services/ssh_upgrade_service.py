"""SSH frpc 客户端扫描与升级"""
from __future__ import annotations

import json
import logging
import os
import re
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
    return {
        "proxy_id": state.proxy_id,
        "credential_id": state.credential_id,
        "install_path": state.install_path,
        "is_ssh_candidate": state.is_ssh_candidate,
        "reachable": state.reachable,
        "platform": state.platform,
        "current_version": state.current_version,
        "target_version": state.target_version,
        "target_package_id": state.target_package_id,
        "upgradeable": state.upgradeable,
        "status": state.status,
        "message": state.message,
        "last_scanned_at": state.last_scanned_at,
        "last_upgraded_at": state.last_upgraded_at,
        "proxy_name": proxy.name if proxy else None,
    }


def _run_cmd(ssh: SSHClientProtocol, cmd: str, timeout: float = 30.0):
    return ssh.exec_command(cmd, timeout=timeout)


def scan_proxy_remote(
    ssh: SSHClientProtocol,
    install_path: str,
) -> Dict[str, Any]:
    """在已连接的 SSH 上收集扫描信息。"""
    install_path = install_path.rstrip("/") or "/opt/frp"
    info: Dict[str, Any] = {"install_path": install_path}

    os_result = _run_cmd(ssh, "uname -s")
    arch_result = _run_cmd(ssh, "uname -m")
    info["os_name"] = os_result.stdout
    info["arch"] = arch_result.stdout

    if os_result.stdout.strip().lower() != "linux":
        info["status"] = "unsupported_platform"
        info["message"] = f"不支持的操作系统: {os_result.stdout}"
        return info

    platform = map_linux_arch(arch_result.stdout)
    if not platform:
        info["status"] = "unsupported_platform"
        info["message"] = f"不支持的架构: {arch_result.stdout}"
        return info
    info["platform"] = platform

    uid_result = _run_cmd(ssh, "id -u")
    info["uid"] = uid_result.stdout
    sudo_result = _run_cmd(ssh, "sudo -n true 2>/dev/null; echo $?")
    info["has_passwordless_sudo"] = sudo_result.stdout.strip().endswith("0")

    frpc_path = f"{install_path}/frpc"
    ver_result = _run_cmd(ssh, f"{frpc_path} --version 2>&1 || true")
    info["current_version_raw"] = ver_result.stdout or ver_result.stderr
    info["current_version"] = normalize_version_display(info["current_version_raw"])

    svc_result = _run_cmd(ssh, "systemctl is-active frpc 2>/dev/null || echo inactive")
    info["service_active"] = svc_result.stdout.strip() == "active"

    writable = _run_cmd(
        ssh,
        f"test -w {install_path} 2>/dev/null && echo ok || (sudo -n test -w {install_path} 2>/dev/null && echo ok_sudo || echo denied)",
    )
    info["writable"] = "ok" in writable.stdout or "ok_sudo" in writable.stdout
    if not info["writable"]:
        info["status"] = "permission_denied"
        info["message"] = f"对 {install_path} 无写权限且无法 sudo"
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
    state.install_path = install_path
    state.is_ssh_candidate = is_ssh_candidate(proxy)
    state.last_scanned_at = now
    state.reachable = remote_info.get("status") == "reachable" or remote_info.get("status") in (
        "latest",
        "upgradeable",
        "no_package",
    )

    status = remote_info.get("status", "unknown")
    state.platform = remote_info.get("platform")
    state.current_version = remote_info.get("current_version")
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


def upgrade_single_proxy(
    db: Session,
    proxy: Proxy,
    credential: SshCredential,
    install_path: str = "/opt/frp",
    auto_scan: bool = True,
    ssh_factory=None,
) -> Dict[str, Any]:
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

    local_frpc = None
    try:
        local_frpc = extract_frpc_binary(package)
    except Exception as e:
        return {"success": False, "proxy_id": proxy.id, "status": "upgrade_failed", "message": str(e)}

    auth_type, password, private_key, passphrase = get_credential_secrets(credential)
    host = ssh_target_host(proxy)
    port = ssh_target_port(proxy)
    install_path = (install_path or state.install_path or "/opt/frp").rstrip("/")
    ts = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    remote_tmp = f"/tmp/frpc.upgrade.{ts}"
    backup_path = f"{install_path}/frpc.bak.upgrade_{ts}"
    frpc_path = f"{install_path}/frpc"

    ssh = ssh_factory(credential) if ssh_factory else _connect_credential(
        auth_type, password, private_key, passphrase
    )
    try:
        if ssh_factory is None:
            ssh.connect(host, port, credential.username)

        # 上传新二进制
        ssh.upload_file(local_frpc, remote_tmp)

        use_sudo = True
        sudo_prefix = "sudo -n " if use_sudo else ""

        def run(cmd: str):
            return _run_cmd(ssh, cmd)

        run(f"{sudo_prefix}systemctl stop frpc 2>/dev/null || true")
        run(f"{sudo_prefix}cp -f {frpc_path} {backup_path} 2>/dev/null || true")
        cp_res = run(f"{sudo_prefix}cp -f {remote_tmp} {frpc_path}")
        if cp_res.exit_code != 0:
            raise RuntimeError(f"复制 frpc 失败: {cp_res.stderr or cp_res.stdout}")
        run(f"{sudo_prefix}chmod 755 {frpc_path}")
        run(f"rm -f {remote_tmp}")
        run(f"{sudo_prefix}systemctl start frpc 2>/dev/null || true")

        ver_res = run(f"{frpc_path} --version 2>&1")
        svc_res = run("systemctl is-active frpc 2>/dev/null || echo inactive")

        new_ver = normalize_version_display(ver_res.stdout or ver_res.stderr)
        if svc_res.stdout.strip() != "active":
            raise RuntimeError(f"frpc 服务未处于 active 状态: {svc_res.stdout}")

        state.status = "upgraded"
        state.upgradeable = False
        state.current_version = new_ver
        state.last_upgraded_at = datetime.utcnow()
        state.message = f"升级成功，当前版本: {new_ver}"
        db.commit()

        return {
            "success": True,
            "proxy_id": proxy.id,
            "status": "upgraded",
            "message": state.message,
            "current_version": new_ver,
        }
    except Exception as e:
        logger.exception("升级失败 proxy_id=%s", proxy.id)
        try:
            run(f"{sudo_prefix}cp -f {backup_path} {frpc_path} 2>/dev/null || true")
            run(f"{sudo_prefix}systemctl start frpc 2>/dev/null || true")
        except Exception:
            pass
        state.status = "upgrade_failed"
        state.message = f"升级失败: {e}"
        db.commit()
        return {
            "success": False,
            "proxy_id": proxy.id,
            "status": "upgrade_failed",
            "message": state.message,
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
            db, proxy, credential, install_path, auto_scan=explicit_ids
        )
        results.append({"proxy_name": proxy.name, **r})
        if r.get("success"):
            success += 1
        else:
            failed += 1

    finish_job(db, job, results, success, failed, skipped)
    return job
