"""Inventory hierarchy, migration and per-service authorization remain independent."""
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from app.auth import get_current_user
from app.database import get_db
from app.main import app
from app.models.host_machine import HostMachine
from app.models.managed_host import ManagedHost, HostAccessGrant
from app.models.frps_server import FrpsServer
from app.models.group import Group
from app.models.ssh_credential import SshCredential
from app.models.user import User
from app.services.credential_encryption import encrypt_secret
from app.services import vnc_service
from test_monitoring import db


def test_hierarchy_move_and_group_changes_never_expand_service_permissions(db):
    server = FrpsServer(name='node',server_addr='node.test',api_base_url='http://node.test/api',auth_username='u',auth_password='not-exposed')
    db.add(server); db.flush()
    db.add(Group(frps_server_id=server.id,name='lab'))
    credential = SshCredential(name='test',username='vnc',auth_type='password',password_encrypted=encrypt_secret('secret'))
    db.add(credential); db.commit()
    user = [User(id=0,role='admin')]
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: user[0]
    try:
        client = TestClient(app)
        machine = client.post('/api/host-machines',json=dict(name='Mac',group_key=f'{server.id}:lab')).json()
        other = client.post('/api/host-machines',json=dict(name='Other')).json()
        payload=dict(machine_id=machine['id'],address='127.0.0.1',credential_id=credential.id)
        ssh = client.post('/api/managed-hosts',json=dict(payload,name='mac-ssh',host_type='ssh',port=2222))
        vnc = client.post('/api/managed-hosts',json=dict(payload,name='mac-vnc',host_type='vnc',port=5900))
        assert ssh.status_code == vnc.status_code == 201
        ssh, vnc = ssh.json(), vnc.json()
        assert not vnc['vnc_ssh_host_id'] and not vnc['host_key_fingerprint']
        assert client.get(f"/api/host-machines/{machine['id']}").json()['service_count']==2
        assert len(client.get('/api/host-machines/groups',params=dict(page=1)).json()['items'])==1
        assert client.delete(f"/api/host-machines/{machine['id']}").status_code==409
        before = db.query(HostMachine).count()
        assert client.post('/api/managed-hosts',json=dict(payload,name='unsafe',host_type='vnc',address='8.8.8.8')).status_code==400
        assert db.query(HostMachine).count()==before
        user[0] = User(id=2,role='user')
        assert client.get('/api/host-machines',params=dict(page=1)).json()['total']==0
        assert client.get(f"/api/host-machines/{machine['id']}").status_code==404
        assert client.post('/api/host-machines',json=dict(name='no')).status_code==403
        assert client.get('/api/host-machines/groups').status_code==403
        db.add(HostAccessGrant(host_id=vnc['id'],subject_type='user',subject_id=2,can_connect=True));db.commit()
        assert client.get(f"/api/host-machines/{machine['id']}").json()['service_count']==1
        visible = client.get('/api/managed-hosts',params=dict(page=1,machine_id=machine['id'])).json()['items']
        assert [row['id'] for row in visible]==[vnc['id']]
        user[0] = User(id=0,role='admin')
        result = client.put(f"/api/managed-hosts/{vnc['id']}",json=dict(machine_id=other['id']))
        assert result.status_code==200 and result.json()['name']==vnc['name']
        assert db.query(HostAccessGrant).count()==1
        user[0] = User(id=2,role='user')
        assert client.get(f"/api/host-machines/{machine['id']}").status_code==404
        assert client.get(f"/api/host-machines/{other['id']}").json()['service_count']==1
        assert client.put(f"/api/managed-hosts/{vnc['id']}",json=dict(machine_id=machine['id'])).status_code==403
        user[0] = User(id=0,role='admin')
        assert client.post('/api/groups/rename',json=dict(old_name='lab',new_name='office',frps_server_id=server.id)).status_code==200
        assert client.get(f"/api/host-machines/{machine['id']}").json()['group_name']=='office'
        assert client.delete('/api/groups/office',params=dict(frps_server_id=server.id)).status_code==200
        assert client.get(f"/api/host-machines/{machine['id']}").json()['group_name'] is None
        assert db.query(ManagedHost).count()==2
        assert db.query(HostAccessGrant).count()==1
    finally:
        app.dependency_overrides.clear()


def test_inventory_migration_is_idempotent_and_does_not_merge_connections(monkeypatch):
    from app.migrations import add_host_machines as migration
    engine = create_engine('sqlite://')
    with engine.begin() as conn:
        conn.execute(text('CREATE TABLE managed_hosts (id INTEGER PRIMARY KEY,name TEXT,description TEXT,credential_id INTEGER)'))
        conn.execute(text("INSERT INTO managed_hosts VALUES (7,'Mac SSH','ssh',11),(9,'Mac VNC','vnc',12)"))
    monkeypatch.setattr(migration,'engine',engine)
    migration.upgrade(); migration.upgrade()
    with engine.connect() as conn:
        rows=conn.execute(text('SELECT id,name,description,credential_id,machine_id FROM managed_hosts ORDER BY id')).all()
        assert [tuple(row[:4]) for row in rows]==[(7,'Mac SSH','ssh',11),(9,'Mac VNC','vnc',12)]
        assert rows[0][4] != rows[1][4]
        assert conn.execute(text('SELECT count(*) FROM host_machines')).scalar()==2
    engine.dispose()


@pytest.mark.parametrize('address',['8.8.8.8','169.254.169.254','0.0.0.0','::','::ffff:8.8.8.8','https://host'])
def test_direct_vnc_rejects_untrusted_or_invalid_addresses(address):
    with pytest.raises(HTTPException): vnc_service.direct_address(address)


def test_vnc_dns_rebinding_and_mixed_answers_never_open_a_socket(monkeypatch):
    monkeypatch.setattr(vnc_service.socket,'getaddrinfo',lambda *a,**k:[(2,1,6,'',('127.0.0.1',5900)),(2,1,6,'',('8.8.8.8',5900))])
    monkeypatch.setattr(vnc_service.socket,'socket',lambda *a:pytest.fail('Untrusted destination was dialled'))
    with pytest.raises(HTTPException): vnc_service.open_direct('vnc.test',5900)
