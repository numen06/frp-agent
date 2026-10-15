"""Resource limits for the public SSH gateway."""

import json
from types import SimpleNamespace

import paramiko

from app.services import ssh_gateway_service as gateway_module


def test_gateway_caps_sessions_globally_and_per_ip(monkeypatch):
    monkeypatch.setattr(gateway_module, "MAX_GATEWAY_SESSIONS", 2)
    monkeypatch.setattr(gateway_module, "MAX_GATEWAY_SESSIONS_PER_IP", 1)
    service = gateway_module.SSHGatewayService()

    assert service._reserve_session(("192.0.2.1", 1001))
    assert not service._reserve_session(("192.0.2.1", 1002))
    assert service._reserve_session(("192.0.2.2", 1003))
    assert not service._reserve_session(("192.0.2.3", 1004))

    service._release_session(("192.0.2.1", 1001))
    assert service._reserve_session(("192.0.2.3", 1004))
    assert service._active_sessions == 2
    assert service._sessions_by_ip == {"192.0.2.2": 1, "192.0.2.3": 1}


def test_gateway_rejects_before_starting_a_thread_when_full(monkeypatch):
    monkeypatch.setattr(gateway_module, "MAX_GATEWAY_SESSIONS", 0)
    client = SimpleNamespace(closed=False)
    client.close = lambda: setattr(client, "closed", True)

    class FakeListener:
        def __init__(self):
            self.calls = 0

        def accept(self):
            self.calls += 1
            if self.calls == 1:
                return client, ("192.0.2.1", 1001)
            raise OSError("listener closed")

    service = gateway_module.SSHGatewayService()
    service._socket = FakeListener()
    service._accept_loop()

    assert client.closed
    assert service._active_sessions == 0


def test_gateway_stops_authentication_after_three_failures(monkeypatch):
    calls = []
    failures = []

    class FakeSession:
        def close(self):
            pass

    monkeypatch.setattr(gateway_module, "SessionLocal", FakeSession)
    monkeypatch.setattr(
        gateway_module,
        "authenticate_gateway_login",
        lambda *_args: calls.append(True) or None,
    )
    server = gateway_module.GatewayServerInterface(
        on_auth_failure=lambda: failures.append(True)
    )

    for _ in range(4):
        assert server.check_auth_password("test#host", "wrong") == paramiko.AUTH_FAILED
    assert len(calls) == 3
    assert len(failures) == 3
    assert server.failed_auth_attempts == 3


def test_gateway_temporarily_blocks_repeated_failed_authentication(monkeypatch):
    now = [1000.0]
    monkeypatch.setattr(gateway_module.time, "monotonic", lambda: now[0])
    monkeypatch.setattr(gateway_module.time, "time", lambda: now[0])
    service = gateway_module.SSHGatewayService()
    ip = "192.0.2.10"

    for _ in range(gateway_module.AUTH_FAILURE_BAN_THRESHOLD - 1):
        service._record_auth_failure(ip)
    assert not service._is_ip_blocked(ip)
    assert not service._is_ip_blocked("192.0.2.11")

    service._record_auth_failure(ip)
    assert service._is_ip_blocked(ip)
    now[0] += gateway_module.AUTH_BAN_SECONDS + 1
    assert not service._is_ip_blocked(ip)


def test_gateway_restores_and_expires_bans_after_restart(tmp_path, monkeypatch):
    now = [1000.0]
    monkeypatch.setattr(gateway_module.time, "monotonic", lambda: now[0])
    monkeypatch.setattr(gateway_module.time, "time", lambda: now[0])
    ban_file = tmp_path / "ssh_gateway_bans.json"
    ip = "192.0.2.20"

    original = gateway_module.SSHGatewayService()
    original._ban_file_path = str(ban_file)
    for _ in range(gateway_module.AUTH_FAILURE_BAN_THRESHOLD):
        original._record_auth_failure(ip)
    assert json.loads(ban_file.read_text(encoding="utf-8"))["bans"][ip] == (
        now[0] + gateway_module.AUTH_BAN_SECONDS
    )

    restarted = gateway_module.SSHGatewayService()
    restarted._ban_file_path = str(ban_file)
    restarted._load_bans()
    assert restarted._is_ip_blocked(ip)

    now[0] += gateway_module.AUTH_BAN_SECONDS + 1
    after_expiry = gateway_module.SSHGatewayService()
    after_expiry._ban_file_path = str(ban_file)
    after_expiry._load_bans()
    assert not after_expiry._is_ip_blocked(ip)
    assert json.loads(ban_file.read_text(encoding="utf-8"))["bans"] == {}


def test_old_auth_failures_do_not_trigger_a_new_ban(monkeypatch):
    now = [1000.0]
    monkeypatch.setattr(gateway_module.time, "monotonic", lambda: now[0])
    service = gateway_module.SSHGatewayService()
    ip = "192.0.2.13"

    for _ in range(gateway_module.AUTH_FAILURE_BAN_THRESHOLD - 1):
        service._record_auth_failure(ip)
    now[0] += gateway_module.AUTH_FAILURE_WINDOW_SECONDS + 1
    service._record_auth_failure(ip)

    assert not service._is_ip_blocked(ip)
    assert len(service._auth_by_ip[ip].attempts) == 1


def test_successful_authentication_clears_ip_failure_history():
    service = gateway_module.SSHGatewayService()
    ip = "192.0.2.12"
    service._record_auth_failure(ip)
    server = gateway_module.GatewayServerInterface(
        on_auth_success=lambda: service._clear_auth_failures(ip)
    )

    assert server._auth_result(SimpleNamespace()) == paramiko.AUTH_SUCCESSFUL
    assert ip not in service._auth_by_ip


def test_gateway_closes_unauthenticated_session_at_deadline(monkeypatch):
    transports = []

    class FakeTransport:
        def __init__(self, _socket):
            self.closed = False
            transports.append(self)

        def add_server_key(self, _key):
            pass

        def start_server(self, *, server):
            pass

        def is_active(self):
            return not self.closed

        def accept(self, _timeout):
            return None

        def close(self):
            self.closed = True

    monkeypatch.setattr(gateway_module.paramiko, "Transport", FakeTransport)
    monkeypatch.setattr(gateway_module, "AUTH_DEADLINE_SECONDS", 0)
    service = gateway_module.SSHGatewayService()
    service._host_key = object()
    client = SimpleNamespace(close=lambda: None)

    service._handle_client(client, ("192.0.2.4", 1005))

    assert transports[0].closed
    assert transports[0].banner_timeout == gateway_module.HANDSHAKE_TIMEOUT_SECONDS
    assert transports[0].handshake_timeout == gateway_module.HANDSHAKE_TIMEOUT_SECONDS
