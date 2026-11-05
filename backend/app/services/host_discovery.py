"""Discover registered proxy services and diagnose the upstream before the target."""
import os
import json
import time
import socket
from urllib.parse import urlsplit, urlunsplit
from concurrent.futures import ThreadPoolExecutor
from threading import Lock
import httpx
from fastapi import HTTPException
from app.models.proxy import Proxy
from app.models.frps_server import FrpsServer
from app.models.managed_host import HostProxySource, ManagedHost
from app.services.monitoring_service import probe_address, probe_ssh

scan_lock = Lock()


def target_address(server):
    if server.is_builtin:
        return os.environ.get("FRP_LOCAL_ADDRESS") or probe_address(server)
    return server.server_addr


def address_aliases(server):
    values = {server.server_addr.lower(), target_address(server).lower()}
    if server.is_builtin:
        values.update({"127.0.0.1", "::1"})
        try:
            import psutil
            values.update(a.address for group in psutil.net_if_addrs().values() for a in group)
        except ImportError:
            pass
    for address in list(values):
        try:
            values.update(item[4][0] for item in socket.getaddrinfo(address, None, type=socket.SOCK_STREAM))
        except OSError:
            pass
    return values


def host_proxy(db, host):
    # VNC loopback belongs to the remote Mac reached through SSH, not this FRP node.
    if host.host_type == "vnc":
        return None
    source = db.get(HostProxySource, host.id)
    if source:
        proxy = db.get(Proxy, source.proxy_id)
        if proxy and proxy.remote_port == host.port and host.address.lower() in address_aliases(proxy.frps_server):
            return proxy
    # Existing manually configured hosts can also be matched, including local NAT addresses.
    matches = [p for p in db.query(Proxy).filter(Proxy.proxy_type == "tcp", Proxy.remote_port == host.port)
               if host.address.lower() in address_aliases(p.frps_server)]
    return matches[0] if len(matches) == 1 else None


def server_snapshot(server):
    if not server.is_active:
        reason = "已关闭" if server.is_builtin else "已停用"
        raise HTTPException(503, f"穿透服务器“{server.name}”{reason}，请先到“穿透服务”恢复服务；相关主机暂时无法连接。")
    try:
        with socket.create_connection((target_address(server), server.server_port), timeout=3):
            pass
    except OSError as exc:
        raise HTTPException(503, f"穿透服务器“{server.name}”无法连接，请先检查服务器运行状态、网络及 FRP 端口；尚未检查目标主机或证书。") from exc
    try:
        with httpx.Client(timeout=3, trust_env=False) as client:
            base = server.api_base_url.rstrip("/")
            parsed = urlsplit(base)
            if server.is_builtin and os.environ.get("FRP_LOCAL_ADDRESS") and parsed.hostname in {"127.0.0.1", "localhost", "::1"}:
                address = target_address(server)
                base = urlunsplit((parsed.scheme, f"{address}:{parsed.port or 80}", parsed.path, "", ""))
            response = client.get(base + "/proxy/tcp", auth=(server.auth_username, server.auth_password))
            response.raise_for_status()
            rows = response.json()["proxies"] or []
            if not isinstance(rows, list) or any(not isinstance(p, dict) or p.get("status") not in {"online", "offline"} for p in rows):
                raise ValueError()
            return {p["name"]: p for p in rows}
    except (httpx.HTTPError, ValueError, KeyError, TypeError) as exc:
        raise HTTPException(503, f"穿透服务器“{server.name}”管理接口异常，无法确认代理状态；请先检查该节点的 API 地址、认证和服务状态。") from exc


def check_upstream(db, host):
    proxy = host_proxy(db, host)
    if not proxy:
        return
    snapshot = server_snapshot(proxy.frps_server)
    live = snapshot.get(proxy.name)
    if not live or live["status"] != "online":
        raise HTTPException(503, f"穿透服务器“{proxy.frps_server.name}”可达，但代理“{proxy.name}”已离线；请检查对应客户端 frpc 和网络，再重试主机连接。")
    conf = live.get("conf") or {}
    live_port = conf.get("remotePort", conf.get("remote_port"))
    if live_port is not None and int(live_port) != host.port:
        raise HTTPException(409, f"代理“{proxy.name}”的远程端口已变化，请同步代理并更新主机连接地址。")


def identify_service(address, port):
    """Classify by wire protocol only, regardless of the proxy name or local port."""
    ssh = probe_ssh(address, port, timeout=1.25)
    if ssh["status"] == "healthy":
        return "ssh", "检测依据：有效 SSH-2.0/1.99 握手标识（未验证登录）", True
    if "ConnectionRefusedError" in ssh["message"]:
        raise ValueError("代理入口拒绝连接，请检查代理监听端口及转发配置")
    from app.services.rdp_gateway_service import probe_rdp_fingerprint
    try:
        probe_rdp_fingerprint(address, port, timeout=2.5)
        return "rdp", "检测依据：RDP 协商、TLS 握手及服务证书（未验证 Windows 登录）", True
    except HTTPException:
        pass
    # Portainer status is public; never try credentials or disable TLS validation.
    for tls in [True, False]:
        try:
            url = ("https" if tls else "http") + "://" + (f"[{address}]" if ":" in address else address) + f":{port}/api/status"
            with httpx.Client(timeout=1.5, trust_env=False) as client:
                deadline = time.monotonic() + 1.5
                with client.stream("GET", url, headers={"Accept-Encoding": "identity"}) as r:
                    r.raise_for_status()
                    if "application/json" not in r.headers.get("content-type", "").lower():
                        raise ValueError("非 JSON 响应")
                    body = bytearray()
                    for chunk in r.iter_raw():
                        if len(body) + len(chunk) > 16384 or time.monotonic() > deadline:
                            raise ValueError("状态响应过大或超时")
                        body.extend(chunk)
                    data = json.loads(body)
                if isinstance(data, dict) and isinstance(data.get("Version"), str) and isinstance(data.get("InstanceID"), str) and data["InstanceID"]:
                    return "docker", "检测依据：Portainer /api/status 返回版本及实例标识（未验证凭据）", tls
        except (httpx.HTTPError, ValueError):
            pass
    raise ValueError("未验证到 SSH、RDP 或 Portainer 协议，不能确认可用；目标无响应、不支持的服务或自签名 HTTPS 需核验后手动添加")


def discover(db, proxy_ids=None):
    proxies = db.query(Proxy).filter(Proxy.proxy_type == "tcp", Proxy.remote_port.between(1, 65535)).order_by(Proxy.id).all()
    candidates = [p for p in proxies if proxy_ids is None or p.id in proxy_ids]
    hosts = db.query(ManagedHost).all()
    aliases = {s.id: address_aliases(s) for s in db.query(FrpsServer)}
    sources = {s.proxy_id: s.host_id for s in db.query(HostProxySource) if db.get(ManagedHost, s.host_id)}
    snapshots = {}
    for server in {p.frps_server_id: p.frps_server for p in candidates}.values():
        try:
            snapshots[server.id] = server_snapshot(server)
        except HTTPException as exc:
            snapshots[server.id] = exc.detail
    rows = []
    work = []
    for p in candidates:
        kind = "unknown"
        address = target_address(p.frps_server)
        existing = sources.get(p.id) or next((h.id for h in hosts if h.host_type != "vnc" and h.port == p.remote_port and h.address.lower() in aliases[p.frps_server_id]), None)
        row = dict(proxy_id=p.id, name=p.name, server_name=p.frps_server.name, host_type=kind, address=address, port=p.remote_port,
                   existing_host_id=existing, available=False, message="", docker_use_tls=True)
        rows.append(row)
        snapshot = snapshots[p.frps_server_id]
        if existing:
            row["host_type"] = next(h.host_type for h in hosts if h.id == existing)
            row["message"] = "已加入主机资源"
        elif isinstance(snapshot, str):
            row["message"] = snapshot
        elif snapshot.get(p.name, {}).get("status") != "online":
            row["message"] = "代理已离线，请先恢复 frpc 连接"
        elif (snapshot[p.name].get("conf") or {}).get("remotePort", p.remote_port) != p.remote_port:
            row["message"] = "代理远程端口已变化，请先同步代理再识别"
        else:
            work.append(row)
    def inspect(row):
        try:
            row["host_type"], row["message"], row["docker_use_tls"] = identify_service(row["address"], row["port"])
            row["available"] = True
        except (HTTPException, ValueError, OSError) as exc:
            row["message"] = str(exc.detail if isinstance(exc, HTTPException) else exc)
    with ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(inspect, work))
    # Same port on different machines is valid; only collapse the same service endpoint.
    seen = []
    for row in sorted(rows, key=lambda r: (not bool(r["existing_host_id"]), not r["available"], r["proxy_id"])):
        proxy = next(p for p in candidates if p.id == row["proxy_id"])
        names = aliases[proxy.frps_server_id]
        duplicate = next((previous for previous, addresses in seen if previous["host_type"] == row["host_type"]
                          and previous["port"] == row["port"] and addresses & names), None)
        if duplicate and not row["existing_host_id"]:
            row["available"] = False
            row["duplicate_proxy_id"] = duplicate["proxy_id"]
            row["message"] = f"与代理“{duplicate['name']}”指向同一主机入口，已排除重复"
        else:
            seen.append((row, names))
    return rows
