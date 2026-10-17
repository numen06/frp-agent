"""Collection bounds, permission isolation, audit maintenance and group lifecycle."""
from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth import get_current_user
from app.database import Base, get_db
from app.main import app
from app.models.api_key import ApiKey
from app.models.docker_credential import DockerCredential
from app.models.frps_server import FrpsServer
from app.models.group import Group
from app.models.managed_host import HostAccessGrant, HostAuditLog, ManagedHost
from app.models.port import PortAllocation
from app.models.proxy import Proxy
from app.models.proxy_ssh_state import ProxySshState
from app.models.client_upgrade_job import ClientUpgradeJob
from app.models.ssh_credential import SshCredential
from app.models.user import User
from app.services.port_service import PortService
from app.services.credential_encryption import decrypt_secret


@pytest.fixture
def api():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    with engine.connect() as connection:
        connection.exec_driver_sql("PRAGMA foreign_keys=ON")
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()
    admin = User(username="admin", password_hash="unused", role="admin", is_active=True)
    member = User(username="member", password_hash="unused", role="user", is_active=True)
    db.add_all([admin, member]); db.flush()
    for i in range(45):
        db.add(FrpsServer(name=f"server-{i:03}", server_addr="example.com", api_base_url="https://example.com/api", auth_username="demo", auth_password="unused"))
        db.add(SshCredential(name=f"ssh-{i:03}", username="demo", auth_type="password"))
        db.add(DockerCredential(name=f"docker-{i:03}", auth_type="api_key"))
        db.add(ApiKey(key=f"hash-{i:03}", description=f"key-{i:03}", is_active=True))
        db.add(User(username=f"user-{i:03}", password_hash="unused", role="user", is_active=True))
    db.flush()
    for i in range(45):
        host = ManagedHost(name=f"host-{i:03}", host_type="ssh", address="host.example.com", credential_id=1)
        db.add(host); db.flush()
        db.add(HostAccessGrant(host_id=host.id, subject_type="user", subject_id=member.id, can_connect=True))
        db.add(Group(name=f"group-{i:03}", frps_server_id=1))
        db.add(Proxy(name=f"group-{i:03}_ssh", group_name=f"group-{i:03}", frps_server_id=1, local_port=22, remote_port=6000+i))
        db.add(PortAllocation(frps_server_id=1, port=6000+i, allocated_to=f"group-{i:03}_ssh"))
    for i in range(65):
        db.add(HostAuditLog(host_id=i % 2 + 1, actor_type="user", actor_id=member.id if i % 2 else admin.id,
            actor_name=member.username if i % 2 else admin.username, action="execute_command", command=f"echo demo-{i}",
            status="failed" if i % 3 == 0 else "success", stdout="demo output", client_ip="192.0.2.10",
            created_at=datetime.utcnow() - timedelta(days=120 if i < 40 else 1)))
    db.commit()
    identity = [admin]
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: identity[0]
    client = TestClient(app, raise_server_exceptions=False)
    try:
        yield client, db, identity, admin, member, engine
    finally:
        app.dependency_overrides.clear()
        client.close(); db.close(); engine.dispose()


@pytest.mark.parametrize("path,total", [
    ("/api/servers", 45), ("/api/api-keys", 45), ("/api/ssh-credentials", 45),
    ("/api/docker-credentials", 45), ("/api/managed-hosts", 45),
    ("/api/managed-hosts/access/subjects", 92), ("/api/managed-hosts/access/grants", 45),
    ("/api/managed-hosts/audit/logs", 65), ("/api/groups", 45), ("/api/ports?frps_server_id=1", 45),
])
def test_collections_use_bounded_sql_pages(api, path, total):
    client, _, _, _, _, engine = api
    base_params = {"frps_server_id": 1} if "?" in path else {}
    path = path.split("?")[0]
    statements = []
    def capture(_connection, _cursor, statement, _parameters, _context, _many):
        statements.append(statement)
    event.listen(engine, "before_cursor_execute", capture)
    try:
        first = client.get(path, params={**base_params, "page": 1})
        assert first.status_code == 200, first.text
        first = first.json()
        assert (first["page_size"], first["total"], len(first["items"])) == (20, total, 20)
        assert any("LIMIT" in statement.upper() and "OFFSET" in statement.upper() for statement in statements)
        second = client.get(path, params={**base_params, "page": 2}).json()
        key = lambda row: (row.get("subject_type"), row.get("id", row.get("group_name")))
        assert not set(map(key, first["items"])) & set(map(key, second["items"]))
        empty = client.get(path, params={**base_params, "page": 999}).json()
        assert empty["items"] == [] and empty["total"] == total
        for invalid in [{"page": 0}, {"page_size": 0}, {"page_size": 101}]:
            assert client.get(path, params={**base_params, **invalid}).status_code == 422
    finally:
        event.remove(engine, "before_cursor_execute", capture)


def test_legacy_arrays_are_bounded_and_search_precedes_paging(api):
    client, *_ = api
    for path in ["servers", "api-keys", "ssh-credentials", "docker-credentials", "managed-hosts", "managed-hosts/access/subjects", "managed-hosts/access/grants", "managed-hosts/audit/logs"]:
        data = client.get("/api/" + path).json()
        assert isinstance(data, list) and len(data) == 20, path
    result = client.get("/api/servers", params={"page": 1, "search": "server-044"}).json()
    assert result["total"] == 1 and result["items"][0]["name"] == "server-044"
    assert client.get("/api/servers", params={"page": 1, "search": "%"}).json()["total"] == 0
    users = client.get("/api/managed-hosts/access/subjects", params={"page": 1, "subject_type": "user"}).json()
    assert users["total"] == 47 and all(row["subject_type"] == "user" for row in users["items"])
    groups = client.get("/api/groups/list", params={"page": 3}).json()
    assert groups["total"] == 45 and len(groups["items"]) == 5


def test_audit_paging_detail_and_maintenance_enforce_identity(api):
    client, db, identity, admin, member, _ = api
    identity[0] = member
    result = client.get("/api/managed-hosts/audit/logs", params={"page": 1}).json()
    assert result["total"] == 32 and all(row["actor_id"] == member.id for row in result["items"])
    own = result["items"][0]
    assert client.get(f"/api/managed-hosts/audit/logs/{own['id']}").json()["stdout"] == "demo output"
    other = db.query(HostAuditLog).filter_by(actor_id=admin.id).first()
    assert client.get(f"/api/managed-hosts/audit/logs/{other.id}").status_code == 404
    for data, path in [({"ids": [own["id"]]}, "delete"), ({"keep_days": 30, "dry_run": False}, "cleanup")]:
        assert client.post("/api/managed-hosts/audit/" + path, json=data).status_code == 403
    identity[0] = User(id=-1, username="api-key", role="admin")
    assert client.get("/api/managed-hosts/audit/logs", params={"page": 1}).json()["total"] == 0
    assert client.post("/api/managed-hosts/audit/delete", json={"ids": [own["id"]]}).status_code == 403


def test_audit_filters_cleanup_preview_and_deletion_marker(api):
    client, db, *_ = api
    filtered = client.get("/api/managed-hosts/audit/logs", params={"page": 1, "host_id": 1, "status": "failed", "search": "demo-", "action": "execute_command"}).json()
    assert filtered["total"] > 0
    assert all(row["host_id"] == 1 and row["status"] == "failed" for row in filtered["items"])
    assert client.get("/api/managed-hosts/audit/logs", params={"page": 1, "start_time": "2026-02-01T00:00:00Z", "end_time": "2026-01-01T00:00:00Z"}).status_code == 422
    preview = client.post("/api/managed-hosts/audit/cleanup", json={"keep_days": 90, "host_id": 1}).json()
    assert preview["count"] == 20 and preview["deleted"] == 0 and db.query(HostAuditLog).count() == 65
    cleaned = client.post("/api/managed-hosts/audit/cleanup", json={"keep_days": 90, "host_id": 1, "dry_run": False}).json()
    assert cleaned["deleted"] == 20
    assert db.query(HostAuditLog).filter_by(action="audit_logs_deleted", host_id=1).count() == 1
    assert db.query(HostAuditLog).filter_by(host_id=2).count() == 32
    remaining = db.query(HostAuditLog).filter_by(action="execute_command", host_id=1).first()
    deleted = client.post("/api/managed-hosts/audit/delete", json={"ids": [remaining.id, remaining.id]}).json()
    assert deleted["deleted"] == 1
    for invalid in [{"keep_days": 0}, {"keep_days": -1}, {"keep_days": 3651}]:
        assert client.post("/api/managed-hosts/audit/cleanup", json=invalid).status_code == 422
    assert client.post("/api/managed-hosts/audit/delete", json={"ids": []}).status_code == 422


def test_group_create_ready_to_use_is_atomic(api, monkeypatch):
    client, db, *_ = api
    created = client.post("/api/groups/create", json={"group_name": "new-demo", "frps_server_id": 1, "create_defaults": True})
    assert created.status_code == 200, created.text
    assert created.json()["created_proxies"] == 3
    assert db.query(Proxy).filter_by(group_name="new-demo").count() == 3
    before = db.query(PortAllocation).count()
    original = PortService.allocate_port
    calls = []
    def fail_second(self, *args, **kwargs):
        calls.append(1)
        if len(calls) == 2:
            raise RuntimeError("simulated allocation failure")
        return original(self, *args, **kwargs)
    monkeypatch.setattr(PortService, "allocate_port", fail_second)
    assert client.post("/api/groups/create", json={"group_name": "failed-demo", "frps_server_id": 1, "create_defaults": True}).status_code == 500
    assert db.query(Group).filter_by(name="failed-demo").count() == 0
    assert db.query(Proxy).filter_by(group_name="failed-demo").count() == 0
    assert db.query(PortAllocation).count() == before


def test_group_delete_requires_confirmation_and_cleans_dependents(api):
    client, db, *_ = api
    proxy = db.query(Proxy).filter_by(name="group-000_ssh").one()
    db.add(ProxySshState(proxy_id=proxy.id, status="unknown"))
    job = ClientUpgradeJob(proxy_id=proxy.id, job_type="scan", scope_type="proxy", status="completed", frps_server_id=1)
    db.add(job); db.commit()
    path = "/api/groups/group-000"
    preview = client.get(path + "/delete-preview", params={"frps_server_id": 1}).json()
    assert preview["proxy_count"] == 1 and preview["port_count"] == 1
    assert client.delete(path, params={"frps_server_id": 1}).status_code == 409
    assert client.delete(path, params={"frps_server_id": 1, "delete_proxies": True, "expected_proxy_count": 0}).status_code == 409
    deleted = client.delete(path, params={"frps_server_id": 1, "delete_proxies": True, "expected_proxy_count": 1})
    assert deleted.status_code == 200, deleted.text
    assert deleted.json()["affected_count"] == 1
    db.expire_all()
    assert db.query(ProxySshState).count() == 0
    assert db.query(Proxy).filter_by(group_name="group-000").count() == 0
    assert db.query(Group).filter_by(name="group-000").count() == 0
    assert not db.query(PortAllocation).filter_by(port=6000).one().is_allocated
    assert db.get(ClientUpgradeJob, job.id).proxy_id is None
    assert db.query(Proxy).filter_by(group_name="group-001").count() == 1


def test_group_delete_rejects_active_job(api):
    client, db, *_ = api
    db.add(ClientUpgradeJob(group_name="group-000", job_type="upgrade", scope_type="group", status="running", frps_server_id=1)); db.commit()
    result = client.delete("/api/groups/group-000", params={"frps_server_id": 1, "delete_proxies": True, "expected_proxy_count": 1})
    assert result.status_code == 409
    assert db.query(Proxy).filter_by(group_name="group-000").count() == 1


@pytest.mark.parametrize("kind", ["ssh", "docker"])
def test_credential_management_preserves_secrets_and_rejects_in_use_delete(api, kind):
    client, db, identity, admin, member, _ = api
    path = f"/api/{kind}-credentials"
    body = {"name": "rotation-demo", "auth_type": "password", "username": "operator", "password": "demo-secret"}
    body.update({"sudo_password": "demo-sudo"} if kind == "ssh" else {"ca_cert": "demo-ca"})
    created = client.post(path, json=body)
    assert created.status_code == 201, created.text
    metadata = created.json(); cid = metadata["id"]
    assert not ({"password", "private_key", "passphrase", "sudo_password", "api_key", "ca_cert"} & metadata.keys())
    model = SshCredential if kind == "ssh" else DockerCredential
    row = db.get(model, cid)
    encrypted = row.password_encrypted
    updated = client.put(f"{path}/{cid}", json={"name": "renamed-demo"})
    assert updated.status_code == 200 and updated.json()["has_password"]
    db.refresh(row); assert row.password_encrypted == encrypted
    optional = "sudo_password" if kind == "ssh" else "ca_cert"
    assert client.put(f"{path}/{cid}", json={"password": "rotated-secret", optional: ""}).status_code == 200
    db.refresh(row); assert decrypt_secret(row.password_encrypted) == "rotated-secret"
    assert not getattr(row, optional + "_encrypted")
    host = ManagedHost(name="bound-demo", host_type=kind, address="host.example.com", **{("credential_id" if kind == "ssh" else "docker_credential_id"): cid})
    db.add(host); db.commit()
    assert client.delete(f"{path}/{cid}").status_code == 409
    for actor in [member, User(id=-1, username="api-key", role="admin")]:
        identity[0] = actor
        assert client.get(path, params={"page": 1}).status_code == 403
        assert client.get(f"{path}/{cid}").status_code == 403
        assert client.post(path, json=body).status_code == 403
        assert client.put(f"{path}/{cid}", json={"name": "denied"}).status_code == 403
        assert client.delete(f"{path}/{cid}").status_code == 403
    identity[0] = admin; db.delete(host); db.commit()
    assert client.delete(f"{path}/{cid}").status_code == 204
    assert client.get(f"{path}/{cid}").status_code == 404


def test_ssh_credential_rotation_cannot_break_authentication_or_rdp(api):
    client, db, *_ = api
    created = client.post("/api/ssh-credentials", json={"name": "windows", "username": "administrator", "auth_type": "password", "password": "demo-password"}).json()
    path = f"/api/ssh-credentials/{created['id']}"
    for payload in [{"password": ""}, {"auth_type": "private_key"}]:
        assert client.put(path, json=payload).status_code == 400
    host = ManagedHost(name="rdp-demo", host_type="rdp", address="host.example.com", credential_id=created["id"])
    db.add(host); db.commit()
    assert client.put(path, json={"auth_type": "private_key", "private_key": "demo-key"}).status_code == 409
    assert client.get(path).json()["auth_type"] == "password"
    assert client.put(path, json={"password": "new-demo-password"}).status_code == 200


def test_ssh_credential_delete_protects_clients_and_preserves_completed_jobs(api):
    client, db, *_ = api
    created = client.post("/api/ssh-credentials", json={"name": "client-demo", "username": "operator", "auth_type": "password", "password": "demo-password"}).json()
    cid = created["id"]; path = f"/api/ssh-credentials/{cid}"
    state = ProxySshState(proxy_id=1, credential_id=cid)
    job = ClientUpgradeJob(credential_id=cid, job_type="scan", scope_type="proxy", status="running")
    db.add_all([state, job]); db.commit()
    assert client.delete(path).status_code == 409
    state.credential_id = None; db.commit()
    assert client.delete(path).status_code == 409
    job.status = "completed"; db.commit()
    assert client.delete(path).status_code == 204
    db.refresh(job)
    assert job.credential_id is None and job.status == "completed"
