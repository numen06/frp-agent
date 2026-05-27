"""SSH 升级功能单元测试"""
import json
from unittest.mock import MagicMock

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models.frps_server import FrpsServer
from app.models.proxy import Proxy
from app.models.ssh_credential import SshCredential
from app.models.frp_package import FrpPackage
from app.services.credential_encryption import decrypt_secret, encrypt_secret
from app.services.frp_version_util import compare_versions, is_upgradeable, parse_version
from app.services.ssh_candidate import is_ssh_candidate
from app.services.ssh_upgrade_service import map_linux_arch
from app.services.ssh_client import CommandResult
from app.services.ssh_upgrade_service import (
    finalize_scan_state,
    generate_upgrade_script,
    get_or_create_ssh_state,
    scan_proxy_remote,
    scan_single_proxy,
    _start_detached_upgrade,
    upgrade_single_proxy,
)


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def test_encrypt_decrypt_roundtrip():
    plain = "secret-password-123"
    enc = encrypt_secret(plain)
    assert enc != plain
    assert decrypt_secret(enc) == plain


def test_parse_version():
    assert parse_version("0.61.1") == (0, 61, 1)
    assert parse_version("v0.61.1") == (0, 61, 1)
    assert parse_version("frpc version 0.61.1") == (0, 61, 1)
    assert parse_version("unknown") is None


def test_compare_versions():
    assert compare_versions("0.60.0", "0.61.1") < 0
    assert compare_versions("0.61.1", "0.61.1") == 0
    assert is_upgradeable("0.60.0", "0.61.1")
    assert not is_upgradeable("0.61.1", "0.61.1")


def test_platform_mapping():
    assert map_linux_arch("x86_64") == "linux_amd64"
    assert map_linux_arch("aarch64") == "linux_arm64"
    assert map_linux_arch("mips") is None


def test_ssh_candidate_detection(db):
    server = FrpsServer(
        name="s1",
        server_addr="1.2.3.4",
        server_port=7000,
        api_base_url="http://x/api",
        auth_username="a",
        auth_password="b",
    )
    db.add(server)
    db.commit()

    proxy = Proxy(
        frps_server_id=server.id,
        name="g_ssh",
        group_name="g",
        proxy_type="tcp",
        local_port=22,
        remote_port=60022,
        status="online",
    )
    db.add(proxy)
    db.commit()
    db.refresh(proxy)
    proxy.frps_server = server

    assert is_ssh_candidate(proxy)

    proxy.local_port = 80
    assert not is_ssh_candidate(proxy)


class FakeSSH:
    def __init__(self, responses=None):
        self.responses = responses or {}
        self.uploaded = []
        self.commands = []

    def connect(self, host, port, username, timeout=15.0):
        pass

    def exec_command(self, command, timeout=30.0):
        self.commands.append(command)
        for key, result in sorted(self.responses.items(), key=lambda item: len(item[0]), reverse=True):
            if key in command:
                return result
        return CommandResult(0, "", "")

    def upload_file(self, local_path, remote_path):
        self.uploaded.append((local_path, remote_path))

    def close(self):
        pass


def test_scan_non_ssh_proxy(db):
    server = FrpsServer(
        name="s1",
        server_addr="1.2.3.4",
        server_port=7000,
        api_base_url="http://x/api",
        auth_username="a",
        auth_password="b",
    )
    db.add(server)
    db.commit()
    proxy = Proxy(
        frps_server_id=server.id,
        name="g_http",
        group_name="g",
        proxy_type="tcp",
        local_port=80,
        remote_port=60080,
        status="online",
    )
    db.add(proxy)
    cred = SshCredential(
        name="c1",
        username="root",
        auth_type="password",
        password_encrypted=encrypt_secret("pass"),
    )
    db.add(cred)
    db.commit()
    db.refresh(proxy)
    proxy.frps_server = server

    state = scan_single_proxy(db, proxy, cred)
    assert state.status == "not_ssh"


def test_scan_upgradeable_with_fake_ssh(db):
    server = FrpsServer(
        name="s1",
        server_addr="1.2.3.4",
        server_port=7000,
        api_base_url="http://x/api",
        auth_username="a",
        auth_password="b",
    )
    db.add(server)
    pkg = FrpPackage(
        version="0.61.1",
        platform="linux_amd64",
        filename="frp.tar.gz",
        file_path="/tmp/x.tar.gz",
        file_size=1,
        is_active=True,
    )
    db.add(pkg)
    db.commit()

    proxy = Proxy(
        frps_server_id=server.id,
        name="g_ssh",
        group_name="g",
        proxy_type="tcp",
        local_port=22,
        remote_port=60022,
        status="online",
    )
    db.add(proxy)
    cred = SshCredential(
        name="c1",
        username="root",
        auth_type="password",
        password_encrypted=encrypt_secret("pass"),
    )
    db.add(cred)
    db.commit()
    db.refresh(proxy)
    proxy.frps_server = server

    fake = FakeSSH(
        responses={
            "uname -s": CommandResult(0, "Linux", ""),
            "uname -m": CommandResult(0, "x86_64", ""),
            "id -u": CommandResult(0, "0", ""),
            "sudo -n true": CommandResult(0, "0", ""),
            "--version": CommandResult(0, "0.60.0", ""),
            "systemctl is-active": CommandResult(0, "active", ""),
            "test -w": CommandResult(0, "ok", ""),
        }
    )

    def factory(_cred):
        return fake

    state = scan_single_proxy(db, proxy, cred, ssh_factory=factory)
    assert state.status == "upgradeable"
    assert state.target_package_id == pkg.id


def test_scan_proxy_remote_unsupported_os():
    fake = FakeSSH(
        responses={
            "uname -s": CommandResult(0, "Darwin", ""),
            "uname -m": CommandResult(0, "x86_64", ""),
        }
    )
    info = scan_proxy_remote(fake, "/opt/frp")
    assert info["status"] == "unsupported_platform"


def test_generate_upgrade_script_writes_status_and_log_paths():
    script = generate_upgrade_script(
        job_id="job-1",
        frpc_bin="/opt/frp/frpc",
        config_path="/opt/frp/frpc.toml",
        install_path="/opt/frp",
        service_name="frpc",
        new_frpc_path="/tmp/frp-agent-upgrade/job-1/frpc.new",
        expected_version="0.61.1",
        verify_mode="skip",
        has_ini=True,
        has_toml=True,
    )

    assert 'STATUS_FILE="/tmp/frp-agent-upgrade/job-1/status.json"' in script
    assert 'LOG_FILE="/tmp/frp-agent-upgrade/job-1/upgrade.log"' in script
    assert "write_status" in script
    assert '"remote_result_path": "$RESULT_FILE"' in script
    assert '"final_state": "$final_state"' in script
    assert "Restored frpc.ini" in script
    assert "Restored frpc.toml" in script


def test_start_detached_upgrade_prefers_systemd_run():
    fake = FakeSSH(
        responses={
            "command -v systemd-run": CommandResult(0, "yes", ""),
            "systemd-run": CommandResult(0, "Running as unit frp-agent-upgrade-job-1.service", ""),
        }
    )

    result = _start_detached_upgrade(
        fake,
        "/tmp/frp-agent-upgrade/job-1/upgrade.sh",
        "/tmp/frp-agent-upgrade/job-1/upgrade.log",
        "/tmp/frp-agent-upgrade/job-1/status.json",
        "job-1",
        use_sudo=False,
    )

    assert result["execution_mode"] == "detached_systemd"
    assert result["remote_task_id"] == "frp-agent-upgrade-job-1"
    assert any("systemd-run" in cmd for cmd in fake.commands)


def test_start_detached_upgrade_falls_back_to_nohup():
    fake = FakeSSH(
        responses={
            "command -v systemd-run": CommandResult(0, "no", ""),
            "nohup setsid": CommandResult(0, "12345", ""),
        }
    )

    result = _start_detached_upgrade(
        fake,
        "/tmp/frp-agent-upgrade/job-1/upgrade.sh",
        "/tmp/frp-agent-upgrade/job-1/upgrade.log",
        "/tmp/frp-agent-upgrade/job-1/status.json",
        "job-1",
        use_sudo=False,
    )

    assert result["execution_mode"] == "detached_nohup"
    assert result["remote_task_id"] == "12345"
    assert any("nohup setsid" in cmd for cmd in fake.commands)


def test_upgrade_single_proxy_launches_detached(db, tmp_path, monkeypatch):
    server = FrpsServer(
        name="s1",
        server_addr="1.2.3.4",
        server_port=7000,
        api_base_url="http://x/api",
        auth_username="a",
        auth_password="b",
    )
    db.add(server)
    db.commit()
    db.refresh(server)

    pkg = FrpPackage(
        version="0.61.1",
        platform="linux_amd64",
        filename="frp.tar.gz",
        file_path="/tmp/x.tar.gz",
        file_size=1,
        is_active=True,
    )
    db.add(pkg)
    proxy = Proxy(
        frps_server_id=server.id,
        name="g_ssh",
        group_name="g",
        proxy_type="tcp",
        local_port=22,
        remote_port=60022,
        status="online",
    )
    db.add(proxy)
    cred = SshCredential(
        name="c1",
        username="root",
        auth_type="password",
        password_encrypted=encrypt_secret("pass"),
    )
    db.add(cred)
    db.commit()
    db.refresh(proxy)
    proxy.frps_server = server

    local_frpc = tmp_path / "frpc"
    local_frpc.write_text("fake frpc")
    monkeypatch.setattr("app.services.ssh_upgrade_service.extract_frpc_binary", lambda _pkg: str(local_frpc))

    fake = FakeSSH(
        responses={
            "uname -s": CommandResult(0, "Linux", ""),
            "uname -m": CommandResult(0, "x86_64", ""),
            "id -u": CommandResult(0, "0", ""),
            "sudo -n true": CommandResult(0, "0", ""),
            "--version": CommandResult(0, "0.60.0", ""),
            "systemctl is-active": CommandResult(0, "active", ""),
            "test -w": CommandResult(0, "ok", ""),
            "command -v systemd-run": CommandResult(0, "yes", ""),
            "systemd-run": CommandResult(0, "Running as unit frp-agent-upgrade-x.service", ""),
        }
    )

    result = upgrade_single_proxy(
        db,
        proxy,
        cred,
        verify_url_base="http://agent.local",
        ssh_factory=lambda _cred: fake,
    )

    assert result["status"] == "running_detached"
    assert result["execution_mode"] == "detached_systemd"
    assert result["connection_lost_expected"] is True
    assert result["final_state"] == "unknown_disconnected"
    assert result["remote_result_path"].endswith("/result.json")
    assert any("systemd-run" in cmd for cmd in fake.commands)
    assert not any(cmd.strip().startswith(("bash /tmp/frp-agent-upgrade", "sudo -n bash /tmp/frp-agent-upgrade")) for cmd in fake.commands)
