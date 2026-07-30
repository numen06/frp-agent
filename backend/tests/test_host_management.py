"""主机管理授权与 Portainer API 单元测试。"""
import base64
from datetime import datetime, timedelta
from types import SimpleNamespace

import pytest
import httpx
import paramiko
from cryptography import x509
from cryptography.hazmat.primitives import serialization
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy import inspect, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth import get_current_user
from app.auth import hash_api_key
from app.database import Base
from app.database import get_db
from app.main import app
from app.migrations import add_host_management_tables
from app.routers.api_key import decrypt_key, encrypt_key
from app.config import get_settings
from app.models.docker_credential import DockerCredential
from app.models.api_key import ApiKey
from app.models.managed_host import HostAccessGrant, ManagedHost
from app.models.ssh_credential import SshCredential
from app.models.user import User
from app.services.credential_encryption import decrypt_secret, encrypt_secret
from app.services.host_access_service import (
    add_audit_log,
    accessible_host_ids,
    list_docker_containers,
    permissions_for,
    require_host_access,
    run_host_command,
    run_docker_action,
    test_docker_connection as check_docker_connection,
)
from app.services.ssh_gateway_service import (
    GatewayServerInterface,
    SSHGatewayService,
    _prepare_gateway_exec,
    authenticate_gateway_login,
    authenticate_gateway_public_key,
    authenticate_gateway_resource,
    parse_gateway_username,
)
from app.services import docker_gateway_service as docker_gateway_module
from app.services import ssh_gateway_service as ssh_gateway_module
from app.services.docker_gateway_service import _decode_basic_auth
from app.services.docker_gateway_service import (
    DockerGatewayService,
    authenticate_docker_client_certificate,
    issue_docker_client_certificate,
)


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def _seed(db):
    admin = User(username="admin", password_hash="x", role="admin", is_active=True)
    member = User(username="member", password_hash="x", role="user", is_active=True)
    ssh_credential = SshCredential(
        name="root-key",
        username="root",
        auth_type="password",
        password_encrypted=encrypt_secret("secret"),
    )
    portainer_credential = DockerCredential(
        name="portainer-key",
        auth_type="api_key",
        api_key_encrypted=encrypt_secret("ptr_test"),
    )
    db.add_all([admin, member, ssh_credential, portainer_credential])
    db.commit()
    ssh_host = ManagedHost(
        name="ssh-1",
        address="10.0.0.1",
        port=22,
        host_type="ssh",
        credential_id=ssh_credential.id,
    )
    docker_host = ManagedHost(
        name="docker-1",
        address="portainer.example.test",
        port=9443,
        host_type="docker",
        docker_credential_id=portainer_credential.id,
        docker_use_tls=True,
        docker_verify_tls=False,
        docker_endpoint_id=7,
    )
    db.add_all([ssh_host, docker_host])
    db.commit()
    return admin, member, ssh_host, docker_host


def test_user_only_sees_granted_hosts_and_permissions(db):
    admin, member, ssh_host, docker_host = _seed(db)
    grant = HostAccessGrant(
        host_id=ssh_host.id,
        subject_type="user",
        subject_id=member.id,
        can_connect=True,
        can_execute=True,
        can_manage_docker=False,
    )
    db.add(grant)
    db.commit()

    assert accessible_host_ids(db, admin) is None
    assert accessible_host_ids(db, member) == [ssh_host.id]
    assert permissions_for(db, member, ssh_host.id) == ["connect", "execute"]
    assert require_host_access(db, member, ssh_host.id, "execute").id == ssh_host.id


def test_expired_grant_is_not_effective(db):
    _, member, ssh_host, _ = _seed(db)
    db.add(
        HostAccessGrant(
            host_id=ssh_host.id,
            subject_type="user",
            subject_id=member.id,
            can_connect=True,
            expires_at=datetime.utcnow() - timedelta(seconds=1),
        )
    )
    db.commit()

    assert accessible_host_ids(db, member) == []
    assert permissions_for(db, member, ssh_host.id) == []


class _Response:
    def __init__(self, status_code=200, text="", payload=None):
        self.status_code = status_code
        self.text = text
        self.content = text.encode("utf-8")
        self.headers = {"content-type": "application/json"}
        self._payload = payload or {}

    def json(self):
        return self._payload


class _FakeHttpClient:
    calls = []
    default_headers = None
    last_base_url = None

    def __init__(self, base_url, verify, timeout, headers):
        self.base_url = base_url
        _FakeHttpClient.last_base_url = base_url
        self.verify = verify
        self.timeout = timeout
        self.headers = dict(headers)
        _FakeHttpClient.default_headers = dict(headers)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def post(self, path, json=None):
        self.calls.append(("POST", path, json, dict(self.headers)))
        return _Response(200, '{"jwt":"token"}', {"jwt": "token"})

    def request(self, method, path, content=None, headers=None):
        self.calls.append((method, path, None, dict(self.headers)))
        if path.endswith("/containers/json?all=true"):
            return _Response(
                200,
                '[{"Id":"abc","Names":["/web"],"Image":"nginx","State":"running"}]',
            )
        return _Response(200, "{}")


def test_portainer_api_key_uses_endpoint_proxy(db, monkeypatch):
    _, _, _, docker_host = _seed(db)
    docker_host = db.query(ManagedHost).filter(ManagedHost.id == docker_host.id).first()
    docker_host.address = "http://portainer.example.test/docker/"
    docker_host.port = 80
    docker_host.docker_use_tls = False
    _FakeHttpClient.calls = []
    monkeypatch.setattr("app.services.host_access_service.httpx.Client", _FakeHttpClient)

    result, _, containers = list_docker_containers(docker_host)
    assert result.exit_code == 0
    assert containers[0]["Names"] == ["/web"]
    assert _FakeHttpClient.default_headers == {"X-API-Key": "ptr_test"}
    assert _FakeHttpClient.last_base_url == "http://portainer.example.test/docker/"
    assert _FakeHttpClient.calls[-1][1] == (
        "/api/endpoints/7/docker/containers/json?all=true"
    )

    action_result, _ = run_docker_action(docker_host, "restart", "web")
    assert action_result.exit_code == 0
    assert _FakeHttpClient.calls[-1][1] == (
        "/api/endpoints/7/docker/containers/web/restart"
    )


def test_portainer_password_exchanges_jwt(db, monkeypatch):
    _, _, _, docker_host = _seed(db)
    credential = docker_host.docker_credential
    credential.auth_type = "password"
    credential.username = "operator"
    credential.password_encrypted = encrypt_secret("p@ss")
    credential.api_key_encrypted = None
    db.commit()
    _FakeHttpClient.calls = []
    monkeypatch.setattr("app.services.host_access_service.httpx.Client", _FakeHttpClient)

    result, _ = check_docker_connection(docker_host)
    assert result.exit_code == 0
    assert _FakeHttpClient.calls[0][0:3] == (
        "POST",
        "/api/auth",
        {"Username": "operator", "Password": "p@ss"},
    )
    assert _FakeHttpClient.calls[1][3]["Authorization"] == "Bearer token"
    assert _FakeHttpClient.calls[1][1] == "/api/endpoints/7"


def test_managed_host_http_create_flow():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    db = Session()
    admin = User(username="admin", password_hash="x", role="admin", is_active=True)
    db.add(admin)
    db.commit()
    db.refresh(admin)

    def override_db():
        yield db

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_user] = lambda: admin
    client = TestClient(app)
    try:
        ssh_credential_response = client.post(
            "/api/ssh-credentials",
            json={
                "name": "ssh-with-sudo",
                "username": "operator",
                "auth_type": "password",
                "password": "login-secret",
                "sudo_password": "sudo-secret",
            },
        )
        assert ssh_credential_response.status_code == 201
        assert ssh_credential_response.json()["has_sudo_password"] is True
        stored_ssh_credential = db.query(SshCredential).filter(
            SshCredential.id == ssh_credential_response.json()["id"]
        ).one()
        assert "sudo-secret" not in stored_ssh_credential.sudo_password_encrypted
        assert decrypt_secret(stored_ssh_credential.sudo_password_encrypted) == "sudo-secret"

        credential_response = client.post(
            "/api/docker-credentials",
            json={
                "name": "portainer-prod",
                "auth_type": "api_key",
                "api_key": "ptr_example",
            },
        )
        assert credential_response.status_code == 201
        credential_id = credential_response.json()["id"]

        host_response = client.post(
            "/api/managed-hosts",
            json={
                "name": "docker-prod",
                "address": "http://portainer.internal/docker/",
                "port": 9443,
                "host_type": "docker",
                "docker_credential_id": credential_id,
                "docker_use_tls": True,
                "docker_verify_tls": True,
                "docker_endpoint_id": 3,
            },
        )
        assert host_response.status_code == 201
        payload = host_response.json()
        assert payload["host_type"] == "docker"
        assert payload["credential_kind"] == "Docker"
        assert payload["docker_endpoint_id"] == 3
        assert payload["credential_id"] is None
        assert payload["address"] == "http://portainer.internal/docker"
        assert payload["port"] == 80
        assert payload["docker_use_tls"] is False
        assert payload["docker_verify_tls"] is False
        assert payload["permissions"] == ["connect", "execute", "docker"]

        user_response = client.post(
            "/api/managed-hosts/access/users",
            json={"username": "operator", "password": "password-123", "role": "user"},
        )
        assert user_response.status_code == 201
        member_id = user_response.json()["id"]
        grant_response = client.post(
            "/api/managed-hosts/access/grants",
            json={
                "host_id": payload["id"],
                "subject_type": "user",
                "subject_id": member_id,
                "can_connect": True,
                "can_execute": False,
                "can_manage_docker": True,
            },
        )
        assert grant_response.status_code == 201
        member = db.query(User).filter(User.id == member_id).first()
        app.dependency_overrides[get_current_user] = lambda: member
        member_hosts = client.get("/api/managed-hosts")
        assert member_hosts.status_code == 200
        assert member_hosts.json()[0]["permissions"] == ["connect", "docker"]
        assert client.get("/api/docker-credentials").status_code == 403
        assert client.get("/api/ssh-credentials").status_code == 403
        assert client.get("/api/api-keys").status_code == 403
    finally:
        app.dependency_overrides.clear()
        db.close()


def test_migration_upgrades_existing_user_table(monkeypatch):
    engine = create_engine("sqlite:///:memory:")
    with engine.begin() as connection:
        connection.execute(text("""
            CREATE TABLE users (
                id INTEGER PRIMARY KEY,
                username VARCHAR(50) NOT NULL,
                password_hash VARCHAR(255) NOT NULL,
                created_at TIMESTAMP
            )
        """))
        connection.execute(text("""
            CREATE TABLE ssh_credentials (
                id INTEGER PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                username VARCHAR(100) NOT NULL,
                auth_type VARCHAR(20) NOT NULL
            )
        """))

    monkeypatch.setattr(add_host_management_tables, "engine", engine)
    add_host_management_tables.upgrade()

    inspector = inspect(engine)
    user_columns = {column["name"] for column in inspector.get_columns("users")}
    host_columns = {
        column["name"] for column in inspector.get_columns("managed_hosts")
    }
    credential_columns = {
        column["name"] for column in inspector.get_columns("docker_credentials")
    }
    ssh_credential_columns = {
        column["name"] for column in inspector.get_columns("ssh_credentials")
    }
    assert {"role", "is_active", "ssh_public_key"} <= user_columns
    assert {
        "docker_credential_id",
        "docker_endpoint_id",
        "docker_verify_tls",
        "version_info",
    } <= host_columns
    assert "api_key_encrypted" in credential_columns
    assert "sudo_password_encrypted" in ssh_credential_columns


def test_sudo_command_sends_password_only_over_stdin(db, monkeypatch):
    _, _, ssh_host, _ = _seed(db)
    ssh_host.credential.sudo_password_encrypted = encrypt_secret("sudo-secret")
    db.commit()

    class FakeSSHClient:
        command = None
        stdin_data = None

        def connect(self, *args, **kwargs):
            pass

        def get_server_fingerprint(self):
            return "SHA256:test"

        def exec_command(self, command, timeout=30.0, stdin_data=None):
            self.command = command
            self.stdin_data = stdin_data
            return SimpleNamespace(exit_code=0, stdout="root", stderr="")

        def close(self):
            pass

    fake = FakeSSHClient()
    monkeypatch.setattr(
        "app.services.host_access_service.build_host_client",
        lambda host, credential: fake,
    )

    result, _, fingerprint = run_host_command(
        ssh_host, "id -u; echo 'safe'", use_sudo=True
    )

    assert result.stdout == "root"
    assert fingerprint == "SHA256:test"
    assert fake.command == "sudo -S -p '' -- sh -c 'id -u; echo '\"'\"'safe'\"'\"''"
    assert "sudo-secret" not in fake.command
    assert fake.stdin_data == "sudo-secret\n"


def test_api_key_encryption_is_authenticated_and_legacy_compatible():
    raw_key = "example-api-key"
    encrypted = encrypt_key(raw_key)
    assert encrypted.startswith("v2:")
    assert raw_key not in encrypted
    assert decrypt_key(encrypted) == raw_key

    settings = get_settings()
    salt = f"{settings.auth_username}{settings.auth_password}".encode()
    legacy = base64.b64encode(
        bytes([ord(char) ^ salt[index % len(salt)] for index, char in enumerate(raw_key)])
    ).decode()
    assert decrypt_key(legacy) == raw_key


def test_gateway_username_and_password_authentication(db):
    _, member, ssh_host, docker_host = _seed(db)
    raw_api_key = "gateway-api-key"
    api_key = ApiKey(
        key=hash_api_key(raw_api_key),
        description="gateway",
        is_active=True,
    )
    db.add(api_key)
    db.commit()
    db.add_all(
        [
            HostAccessGrant(
                host_id=ssh_host.id,
                subject_type="user",
                subject_id=member.id,
                can_connect=True,
                can_execute=True,
            ),
            HostAccessGrant(
                host_id=ssh_host.id,
                subject_type="api_key",
                subject_id=api_key.id,
                can_connect=True,
                can_execute=True,
            ),
            HostAccessGrant(
                host_id=docker_host.id,
                subject_type="api_key",
                subject_id=api_key.id,
                can_connect=True,
                can_manage_docker=True,
            ),
        ]
    )
    # authenticate_user 需要真实 bcrypt 哈希。
    from app.auth import get_password_hash

    member.password_hash = get_password_hash("member-password")
    member_key = paramiko.RSAKey.generate(1024)
    member.ssh_public_key = f"{member_key.get_name()} {member_key.get_base64()}"
    db.commit()

    assert parse_gateway_username("member#ssh-1") == ("user", "member", "ssh-1")
    assert parse_gateway_username("ssh-1") == ("api_key", None, "ssh-1")
    assert authenticate_gateway_login(
        db, "member#ssh-1", "member-password"
    ).host_id == ssh_host.id
    public_key_context = authenticate_gateway_public_key(
        db, "member#ssh-1", member_key
    )
    assert public_key_context.host_id == ssh_host.id
    assert public_key_context.mode == "public_key"
    assert authenticate_gateway_public_key(db, "ssh-1", member_key) is None
    assert authenticate_gateway_login(db, "ssh-1", raw_api_key).mode == "api_key"
    assert authenticate_gateway_login(db, "member#ssh-1", "wrong") is None
    assert (
        authenticate_gateway_resource(
            db,
            "docker-1",
            raw_api_key,
            host_type="docker",
            permission="docker",
        ).host_id
        == docker_host.id
    )
    assert (
        authenticate_gateway_resource(
            db,
            "docker-1",
            raw_api_key,
            host_type="docker",
            permission="execute",
        )
        is None
    )


def test_docker_gateway_basic_auth_parser():
    encoded = base64.b64encode("member#docker-1:password".encode()).decode()
    assert _decode_basic_auth(f"Basic {encoded}") == [
        "member#docker-1",
        "password",
    ]
    assert _decode_basic_auth("Bearer token") is None


def test_docker_client_certificate_reuses_registered_ssh_key(
    db, tmp_path, monkeypatch
):
    admin, _, _, docker_host = _seed(db)
    user_key = paramiko.RSAKey.generate(1024)
    admin.ssh_public_key = f"{user_key.get_name()} {user_key.get_base64()}"
    db.commit()
    monkeypatch.setattr(
        docker_gateway_module,
        "get_settings",
        lambda: SimpleNamespace(
            docker_gateway_tls_cert_path=str(tmp_path / "ca.pem"),
            docker_gateway_tls_key_path=str(tmp_path / "ca-key.pem"),
            docker_gateway_tls_common_name="gateway.test",
        ),
    )

    certificate = x509.load_pem_x509_certificate(
        issue_docker_client_certificate(admin, docker_host)
    )
    context = authenticate_docker_client_certificate(
        db, certificate.public_bytes(serialization.Encoding.DER)
    )

    assert context.host_id == docker_host.id
    assert context.user.id == admin.id
    assert context.mode == "client_certificate"
    assert (
        certificate.public_key().public_bytes(
            serialization.Encoding.OpenSSH,
            serialization.PublicFormat.OpenSSH,
        ).decode()
        == admin.ssh_public_key
    )


def test_gateway_session_audit_accepts_no_command_result(db):
    admin, _, ssh_host, _ = _seed(db)
    row = add_audit_log(
        db,
        ssh_host,
        admin,
        "ssh_gateway_session",
        "success",
        "127.0.0.1",
        duration_ms=123,
    )
    assert row.status == "success"
    assert row.stderr == ""
    assert row.exit_code is None


def test_gateway_tracks_requests_per_channel():
    class Channel:
        def __init__(self, channel_id):
            self.channel_id = channel_id

        def get_id(self):
            return self.channel_id

    server = GatewayServerInterface()
    first = Channel(1)
    second = Channel(2)
    third = Channel(3)
    assert server.check_channel_request("session", 1) == paramiko.OPEN_SUCCEEDED
    assert server.check_channel_request("session", 2) == paramiko.OPEN_SUCCEEDED
    assert server.check_channel_request("session", 3) == paramiko.OPEN_SUCCEEDED
    assert server.check_channel_exec_request(first, b"whoami")
    assert server.check_channel_shell_request(second)
    assert server.check_channel_subsystem_request(third, "sftp")

    first_request = server.get_channel_request(1)
    second_request = server.get_channel_request(2)
    third_request = server.get_channel_request(3)
    assert first_request.request_type == "exec"
    assert first_request.exec_command == "whoami"
    assert second_request.request_type == "shell"
    assert second_request.exec_command is None
    assert third_request.request_type == "subsystem"
    assert third_request.subsystem_name == "sftp"
    assert not server.check_channel_subsystem_request(Channel(4), "netconf")


def test_gateway_only_autofills_exact_admin_sudo_command(db):
    admin, member, ssh_host, _ = _seed(db)

    command, password = _prepare_gateway_exec(ssh_host, admin, " sudo -i ")
    assert command == "sudo -S -p '' -i"
    assert password == "secret"
    assert "secret" not in command
    assert _prepare_gateway_exec(ssh_host, member, "sudo -i") == ("sudo -i", None)
    assert _prepare_gateway_exec(ssh_host, admin, "sudo id") == ("sudo id", None)


def test_gateway_accepts_multiple_channels_on_one_transport(monkeypatch):
    class Channel:
        def __init__(self, channel_id):
            self.channel_id = channel_id

        def get_id(self):
            return self.channel_id

        def close(self):
            pass

    class ClientSocket:
        def close(self):
            pass

    class Transport:
        def __init__(self, _socket):
            self.channels = [Channel(1), Channel(2)]
            self.active = True
            self.local_version = None

        def add_server_key(self, _key):
            pass

        def start_server(self, server):
            server.auth_context = SimpleNamespace(host_id=1)

        def is_active(self):
            return self.active

        def accept(self, _timeout):
            if self.channels:
                return self.channels.pop(0)
            self.active = False
            return None

        def close(self):
            self.active = False

    handled = []
    service = SSHGatewayService()
    service._host_key = object()
    service._handle_channel = (
        lambda inbound, _server, _address: handled.append(inbound.get_id())
    )
    monkeypatch.setattr(
        "app.services.ssh_gateway_service.paramiko.Transport", Transport
    )

    service._handle_client(ClientSocket(), ("127.0.0.1", 12345))
    assert sorted(handled) == [1, 2]


def test_gateway_server_keys_are_persistent(tmp_path, monkeypatch):
    ssh_key_path = tmp_path / "ssh_gateway_key"
    monkeypatch.setattr(
        ssh_gateway_module,
        "get_settings",
        lambda: SimpleNamespace(ssh_gateway_host_key_path=str(ssh_key_path)),
    )
    first_service = SSHGatewayService()
    first_key = first_service._load_or_create_host_key()
    second_service = SSHGatewayService()
    second_key = second_service._load_or_create_host_key()
    assert ssh_key_path.exists()
    assert first_key.get_fingerprint() == second_key.get_fingerprint()

    cert_path = tmp_path / "docker_gateway_cert.pem"
    tls_key_path = tmp_path / "docker_gateway_key.pem"
    monkeypatch.setattr(
        docker_gateway_module,
        "get_settings",
        lambda: SimpleNamespace(
            docker_gateway_tls_cert_path=str(cert_path),
            docker_gateway_tls_key_path=str(tls_key_path),
            docker_gateway_tls_common_name="gateway.example.test",
        ),
    )
    returned_cert, returned_key = docker_gateway_module._ensure_tls_certificate()
    assert returned_cert == str(cert_path)
    assert returned_key == str(tls_key_path)
    assert cert_path.read_text(encoding="ascii").startswith("-----BEGIN CERTIFICATE-----")
    assert docker_gateway_module.docker_gateway_certificate_fingerprint().startswith(
        "SHA256:"
    )


def test_gateway_listeners_start_and_stop(tmp_path, monkeypatch):
    ssh_key_path = tmp_path / "listener_ssh_key"
    monkeypatch.setattr(
        ssh_gateway_module,
        "get_settings",
        lambda: SimpleNamespace(
            ssh_gateway_enabled=True,
            ssh_gateway_host="127.0.0.1",
            ssh_gateway_port=0,
            ssh_gateway_host_key_path=str(ssh_key_path),
        ),
    )
    ssh_service = SSHGatewayService()
    ssh_service.start()
    try:
        assert ssh_service.running
        assert ssh_service._socket.getsockname()[1] > 0
    finally:
        ssh_service.stop()

    cert_path = tmp_path / "listener_cert.pem"
    tls_key_path = tmp_path / "listener_key.pem"
    monkeypatch.setattr(
        docker_gateway_module,
        "get_settings",
        lambda: SimpleNamespace(
            docker_gateway_enabled=True,
            docker_gateway_host="127.0.0.1",
            docker_gateway_port=0,
            docker_gateway_tls_cert_path=str(cert_path),
            docker_gateway_tls_key_path=str(tls_key_path),
            docker_gateway_tls_common_name="127.0.0.1",
        ),
    )
    docker_service = DockerGatewayService()
    docker_service.start()
    try:
        port = docker_service._server.server_port
        response = httpx.get(
            f"https://127.0.0.1:{port}/_gateway/health",
            verify=False,
            timeout=5,
        )
        assert response.status_code == 200
        assert response.json()["service"] == "docker-gateway"
    finally:
        docker_service.stop()
