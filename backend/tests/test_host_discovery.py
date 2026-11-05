"""Discovery, activation, upstream priority and privilege boundaries."""
from types import SimpleNamespace
from contextlib import nullcontext
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.auth import get_current_user
from app.database import Base, get_db
from app.models.user import User
from app.models.frps_server import FrpsServer
from app.models.proxy import Proxy
from app.models.managed_host import ManagedHost, HostProxySource, HostAccessGrant
from app.models.ssh_credential import SshCredential
from app.services import host_discovery as service
from app.routers import managed_host as router
from app.services.ssh_client import CommandResult
from app.webssh import app


@pytest.fixture
def env(monkeypatch):
    engine=create_engine("sqlite://",connect_args={"check_same_thread":False},poolclass=StaticPool)
    Base.metadata.create_all(engine); factory=sessionmaker(bind=engine)
    actor=[User(id=0,username="admin",role="admin",password_hash="")]
    with factory() as db:
        s=FrpsServer(id=1,name="node",server_addr="192.0.2.10",server_port=7000,api_base_url="http://node/api",auth_username="x",auth_password="x",is_active=True)
        db.add(s);db.flush()
        for i,(name,port) in enumerate([("pc_ssh",22),("pc_rdp",3389),("pc_web",80),("off_ssh",22)],1):
            db.add(Proxy(id=i,frps_server_id=1,name=name,local_ip="127.0.0.1",local_port=port,remote_port=6000+i,proxy_type="tcp",status="online"))
        db.commit()
    def session():
        with factory() as db:yield db
    app.dependency_overrides[get_db]=session
    app.dependency_overrides[get_current_user]=lambda:actor[0]
    monkeypatch.setattr(service,"address_aliases",lambda s:{s.server_addr})
    monkeypatch.setattr(service,"server_snapshot",lambda s:{"pc_ssh":{"status":"online"},"pc_rdp":{"status":"online"},"pc_web":{"status":"online"},"off_ssh":{"status":"offline"}})
    probes=[]
    def inspect(a,p):
        probes.append((a,p))
        if p == 6003: raise ValueError("不支持的协议")
        return ("rdp" if p == 6002 else "ssh"), "protocol verified", True
    monkeypatch.setattr(service,"identify_service",inspect)
    with TestClient(app) as client:yield client,factory,actor,probes
    app.dependency_overrides.clear();engine.dispose()


def test_scan_protocol_not_online_and_bulk_idempotence(env):
    client,factory,_,probes=env
    rows=client.post("/api/managed-hosts/discovery/scan").json()["items"]
    assert {r["proxy_id"] for r in rows}=={1,2,3,4}
    assert [r["available"] for r in rows]==[True,True,False,False]
    assert {p[1] for p in probes}=={6001,6002,6003}
    assert client.post("/api/managed-hosts/discovery/import",json={"proxy_ids":[1,4]}).status_code==409
    with factory() as db:assert db.query(ManagedHost).count()==0
    result=client.post("/api/managed-hosts/discovery/import",json={"proxy_ids":[1,2,1]}).json()
    assert len(result["created_ids"])==2
    again=client.post("/api/managed-hosts/discovery/import",json={"proxy_ids":[1,2]}).json()
    assert again["created_ids"]==[] and len(again["existing_ids"])==2
    data=client.get("/api/managed-hosts?page=1&host_status=pending").json()
    assert data["total"]==2 and all(h["activation_pending"] and not h["is_active"] for h in data["items"])
    assert client.get("/api/managed-hosts?page=1&host_status=disabled").json()["total"]==0
    with factory() as db:assert db.query(HostAccessGrant).count()==0


def test_incomplete_and_failed_tests_do_not_activate_success_does(env,monkeypatch):
    client,factory,_,_=env
    hid=client.post("/api/managed-hosts/discovery/import",json={"proxy_ids":[1]}).json()["created_ids"][0]
    monkeypatch.setattr(service,"check_upstream",lambda db,h:None)
    assert client.post(f"/api/managed-hosts/{hid}/test").status_code==400
    with factory() as db:
        credential=SshCredential(name="ssh",username="root",auth_type="password");db.add(credential);db.commit();cid=credential.id
    r=client.put(f"/api/managed-hosts/{hid}",json={"credential_id":cid,"is_active":True})
    assert r.status_code==200 and not r.json()["is_active"] and r.json()["activation_pending"]
    monkeypatch.setattr(router,"run_host_command",lambda *a:(CommandResult(1,"","auth failed"),5,None))
    assert client.post(f"/api/managed-hosts/{hid}/test").json()["success"] is False
    with factory() as db:assert not db.get(ManagedHost,hid).is_active and db.get(HostProxySource,hid).activation_pending
    monkeypatch.setattr(router,"run_host_command",lambda *a:(CommandResult(0,"Linux",""),5,"SHA256:test"))
    assert client.post(f"/api/managed-hosts/{hid}/test").json()["success"] is True
    with factory() as db:
        assert db.get(ManagedHost,hid).is_active and not db.get(HostProxySource,hid).activation_pending
        db.get(ManagedHost,hid).is_active=False;db.commit()
    # A deliberately disabled, previously activated host must not be auto-enabled.
    client.post(f"/api/managed-hosts/{hid}/test")
    with factory() as db:assert not db.get(ManagedHost,hid).is_active
    assert client.delete(f"/api/managed-hosts/{hid}").status_code==204
    with factory() as db:assert db.get(HostProxySource,hid) is None


def test_access_and_existing_host_endpoint_dedup(env):
    client,factory,actor,_=env
    with factory() as db:
        db.add(ManagedHost(name="manual",host_type="ssh",address="192.0.2.10",port=6001));db.commit()
    r=client.post("/api/managed-hosts/discovery/import",json={"proxy_ids":[1]}).json()
    assert not r["created_ids"] and len(r["existing_ids"])==1
    actor[0]=User(id=2,username="member",role="user",password_hash="x")
    for path in ["scan","import"]:
        assert client.post("/api/managed-hosts/discovery/"+path,json={"proxy_ids":[2]}).status_code==403
    assert client.get("/api/managed-hosts/ssh-protection").status_code==403
    assert client.get("/api/managed-hosts?page=1&host_status=pending").json()["total"]==0
    assert client.post("/api/managed-hosts/1/test").status_code==403


def test_upstream_error_preserved_before_target_probe(env,monkeypatch):
    client,factory,_,_=env
    with factory() as db:
        db.add(ManagedHost(id=5,name="rdp",host_type="rdp",address="192.0.2.10",port=6002));db.commit()
    def upstream(db,h):raise HTTPException(503,"穿透服务器“node”无法连接")
    monkeypatch.setattr(service,"check_upstream",upstream)
    monkeypatch.setattr(router,"test_rdp_connection",lambda h:pytest.fail("must not probe target certificate"))
    r=client.post("/api/managed-hosts/5/test")
    assert r.status_code==503 and r.json()["detail"]=="穿透服务器“node”无法连接"
    with factory() as db:assert db.get(ManagedHost,5).last_message==r.json()["detail"]


def test_live_upstream_server_then_proxy_not_cached_status(env,monkeypatch):
    _,factory,_,_=env
    monkeypatch.setattr(service,"server_snapshot",lambda s:{"pc_rdp":{"status":"offline"}})
    with factory() as db:
        host=ManagedHost(id=-1,address="192.0.2.10",port=6002)
        with pytest.raises(HTTPException,match="代理.*离线"):service.check_upstream(db,host)
        monkeypatch.setattr(service,"server_snapshot",lambda s:{"pc_rdp":{"status":"online","conf":{"remotePort":7002}}})
        with pytest.raises(HTTPException,match="端口已变化"):service.check_upstream(db,host)
        monkeypatch.setattr(service,"server_snapshot",lambda s:{"pc_rdp":{"status":"online"}})
        service.check_upstream(db,host)


def test_server_failures_are_actionable(monkeypatch):
    server=SimpleNamespace(name="node",is_active=False,is_builtin=False)
    with pytest.raises(HTTPException,match="穿透服务器.*已停用"):service.server_snapshot(server)
    server.is_active=True;server.server_addr="192.0.2.10";server.server_port=7000
    def refused(*a,**kw):raise ConnectionRefusedError()
    monkeypatch.setattr(service.socket,"create_connection",refused)
    with pytest.raises(HTTPException,match="尚未检查目标主机或证书"):service.server_snapshot(server)


def test_protection_reads_persisted_active_bans_and_rejects_corrupt(env,monkeypatch,tmp_path):
    import time,json
    from app.config import get_settings
    client,_,_,_=env
    monkeypatch.setattr(get_settings(),"ssh_gateway_host_key_path",str(tmp_path/"key"))
    path=tmp_path/"ssh_gateway_bans.json"
    path.write_text(json.dumps({"version":1,"bans":{"192.0.2.1":time.time()+600,"192.0.2.2":time.time()-5}}))
    data=client.get("/api/managed-hosts/ssh-protection").json()
    assert len(data["bans"])==1 and data["bans"][0]["ip"]=="192.0.2.1"
    assert data["policy"]["ban_threshold"]==10 and data["webssh"]["max_per_user"]==4
    path.write_text("corrupt")
    assert client.get("/api/managed-hosts/ssh-protection").status_code==503


def test_same_endpoint_excluded_but_same_port_on_other_server_allowed(env,monkeypatch):
    client,factory,_,_=env
    with factory() as db:
        for sid,address in [(2,"192.0.2.20"),(3,"192.0.2.10")]:
            db.add(FrpsServer(id=sid,name=f"node-{sid}",server_addr=address,server_port=7000,api_base_url="http://node/api",auth_username="x",auth_password="x",is_active=True))
        db.flush()
        db.add_all([Proxy(id=5,name="other_ssh",frps_server_id=2,local_port=22,remote_port=6001,proxy_type="tcp",status="online"),Proxy(id=6,name="duplicate_ssh",frps_server_id=3,local_port=22,remote_port=6001,proxy_type="tcp",status="online")]);db.commit()
    monkeypatch.setattr(service,"server_snapshot",lambda s:{name:{"status":"online"} for name in ["pc_ssh","pc_rdp","other_ssh","duplicate_ssh"]})
    rows={r["proxy_id"]:r for r in client.post("/api/managed-hosts/discovery/scan").json()["items"]}
    assert rows[1]["available"] and rows[5]["available"]
    assert not rows[6]["available"] and rows[6]["duplicate_proxy_id"]==1
    assert client.post("/api/managed-hosts/discovery/import",json={"proxy_ids":[1,6]}).status_code==409
    with factory() as db:assert db.query(ManagedHost).count()==0
    r=client.post("/api/managed-hosts/discovery/import",json={"proxy_ids":[1,5]})
    assert r.status_code==200 and len(r.json()["created_ids"])==2
    with factory() as db:
        assert {(h.address,h.port) for h in db.query(ManagedHost)}=={("192.0.2.10",6001),("192.0.2.20",6001)}


def test_metrics_returns_real_count_and_marks_corrupt_or_stale(env,monkeypatch,tmp_path):
    import time,json
    from app.config import get_settings
    client,_,_,_=env
    monkeypatch.setattr(get_settings(),"ssh_gateway_host_key_path",str(tmp_path/"key"))
    path=tmp_path/"ssh_gateway_metrics.json"
    metrics={"version":1,"counts":{"auth_failures":21,"auth_successes":3},"collected_at":time.time(),"first_log_at":"2026-11-02T00:00:00Z","started_at":"2026-11-02T00:00:00Z"}
    path.write_text(json.dumps(metrics));r=client.get("/api/managed-hosts/ssh-protection").json()
    assert r["native_metrics"]["counts"]["auth_failures"]==21 and not r["metrics_error"]
    metrics["collected_at"]=time.time()-200;path.write_text(json.dumps(metrics))
    assert "过期" in client.get("/api/managed-hosts/ssh-protection").json()["metrics_error"]
    path.write_text("corrupt");r=client.get("/api/managed-hosts/ssh-protection").json()
    assert r["native_metrics"] is None and "读取失败" in r["metrics_error"]


def test_arbitrary_name_and_nonstandard_port_detected_by_protocol(env,monkeypatch):
    client,factory,_,probes=env
    with factory() as db:
        p=db.get(Proxy,1);p.name="anything-123";p.local_port=45678;db.commit()
    monkeypatch.setattr(service,"server_snapshot",lambda s:{"anything-123":{"status":"online"}})
    rows=client.post("/api/managed-hosts/discovery/scan").json()["items"]
    row=next(r for r in rows if r["proxy_id"]==1)
    assert row["available"] and row["host_type"]=="ssh" and ("192.0.2.10",6001) in probes


def test_vnc_loopback_does_not_match_or_exclude_frp_proxy(env,monkeypatch):
    client,factory,_,_=env
    monkeypatch.setattr(service,"address_aliases",lambda s:{s.server_addr,"127.0.0.1"})
    with factory() as db:
        host=ManagedHost(name="mac-desktop",host_type="vnc",address="127.0.0.1",port=6001)
        db.add(host);db.commit()
        assert service.host_proxy(db,host) is None
    rows=client.post("/api/managed-hosts/discovery/scan").json()["items"]
    row=next(r for r in rows if r["proxy_id"]==1)
    assert row["available"] and row["existing_host_id"] is None
    result=client.post("/api/managed-hosts/discovery/import",json={"proxy_ids":[1]})
    assert result.status_code==200 and len(result.json()["created_ids"])==1


def test_real_ssh_handshake_on_random_port():
    import socket,threading
    listener=socket.create_server(("127.0.0.1",0));port=listener.getsockname()[1]
    received=[]
    def serve():
        with listener:
            conn,_=listener.accept()
            with conn:
                conn.sendall(b"SSH-2.0-real-test-server\r\n")
                received.append(conn.recv(100))
    thread=threading.Thread(target=serve,daemon=True);thread.start()
    kind,message,tls=service.identify_service("127.0.0.1",port)
    thread.join(3)
    assert kind=="ssh" and "SSH-2.0/1.99" in message
    assert received==[b""]  # Identification only; no password or command sent.


def test_rdp_identified_by_negotiation_not_port(monkeypatch):
    from app.services import rdp_gateway_service as rdp
    calls=[]
    monkeypatch.setattr(service,"probe_ssh",lambda *a,**kw:dict(status="failed",message="not SSH"))
    monkeypatch.setattr(rdp,"probe_rdp_fingerprint",lambda a,p,**kw:calls.append((a,p)) or "SHA256:"+"a"*64)
    kind,message,_=service.identify_service("127.0.0.1",45678)
    assert kind=="rdp" and "TLS" in message and calls==[("127.0.0.1",45678)]


@pytest.mark.parametrize("payload,expected",[({"Version":"2.27.6","InstanceID":"test-instance"},"docker"),({"Version":"1.0"},None)])
def test_portainer_requires_actual_status_signature(payload,expected):
    import json,threading
    from http.server import ThreadingHTTPServer,BaseHTTPRequestHandler
    paths=[]
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*a):pass
        def do_GET(self):
            paths.append(self.path)
            self.send_response(200);self.send_header("Content-Type","application/json");self.end_headers()
            self.wfile.write(json.dumps(payload).encode())
    server=ThreadingHTTPServer(("127.0.0.1",0),Handler)
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    try:
        if expected:
            kind,message,tls=service.identify_service("127.0.0.1",server.server_port)
            assert kind==expected and not tls and "/api/status" in message
        else:
            with pytest.raises(ValueError,match="未验证到"):service.identify_service("127.0.0.1",server.server_port)
        assert paths==["/api/status"]
    finally:
        server.shutdown();server.server_close();thread.join(2)
