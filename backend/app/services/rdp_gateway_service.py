"""Native mstsc gateway: platform authentication, stored credentials and bounded relays."""
import hashlib
import hmac
import ipaddress
import logging
import os
import re
import secrets
import shutil
import socket
import ssl
import subprocess
import select
import tempfile
from dataclasses import dataclass, field
import threading
import time
from collections import OrderedDict
from urllib.parse import urlsplit

from fastapi import HTTPException

from app.config import get_settings
from app.database import SessionLocal
from app.models.managed_host import ManagedHost
from app.services.credential_encryption import decrypt_secret
from app.services.ssh_gateway_service import authenticate_gateway_resource, parse_gateway_username, _authorize_gateway_identity
from app.services.rdp_auth_service import ntlm_verifier
from app.models.api_key import ApiKey
from app.models.user import User
from app.services.host_access_service import add_audit_log, require_host_access
from app.services.ssh_client import CommandResult

logger = logging.getLogger(__name__)
SESSION_SECONDS = 8 * 60 * 60


def normalize_ip(value):
    address = ipaddress.ip_address(value)
    return str(address.ipv4_mapped or address) if address.version == 6 else str(address)


def rdp_client_ip(request):
    """Walk the proxy chain from the socket peer; never trust arbitrary XFF."""
    try:
        peer = normalize_ip(request.client.host)
        trusted = [
            ipaddress.ip_network(value.strip())
            for value in get_settings().rdp_gateway_trusted_proxies.split(",")
            if value.strip()
        ]
        chain = request.headers.get("x-forwarded-for", "").split(",")
        for value in reversed(chain):
            if not any(ipaddress.ip_address(peer) in network for network in trusted):
                break
            if value.strip():
                peer = normalize_ip(value.strip())
        return peer
    except (ValueError, AttributeError):
        raise HTTPException(status_code=400, detail="RDP 客户端来源 IP 无效")


def require_secure_rdp_download(request):
    if request.url.scheme == "https":
        return
    try:
        peer = ipaddress.ip_address(normalize_ip(request.client.host))
        trusted = [ipaddress.ip_network(value.strip())
                   for value in get_settings().rdp_gateway_trusted_proxies.split(",") if value.strip()]
        if any(peer in network for network in trusted) and request.headers.get("x-forwarded-proto") == "https":
            return
    except (ValueError, AttributeError):
        pass
    raise HTTPException(status_code=400, detail="请通过 HTTPS 下载 RDP 连接文件")


def validate_rdp_address(address):
    try:
        return str(ipaddress.ip_address(address))
    except ValueError:
        if len(address) > 253 or not all(
            re.fullmatch(r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?", label)
            for label in address.split(".")
        ):
            raise HTTPException(status_code=400, detail="RDP 地址只允许主机名或 IP")
        return address.lower()


def rdp_target(host):
    address = validate_rdp_address(host.address)
    return f"[{address}]:{host.port}" if ":" in address else f"{address}:{host.port}"


def probe_rdp_fingerprint(address, port):
    """Inspect the target certificate without sending any Windows credentials."""
    address = validate_rdp_address(address.strip())
    if not 1 <= port <= 65535:
        raise HTTPException(status_code=400, detail="RDP 端口无效")
    deadline = time.monotonic() + 8

    def remaining():
        seconds = deadline - time.monotonic()
        if seconds <= 0:
            raise TimeoutError()
        return seconds

    def read(sock, size):
        data = b""
        while len(data) < size:
            sock.settimeout(remaining())
            chunk = sock.recv(size - len(data))
            if not chunk:
                raise ValueError("RDP 协商提前结束")
            data += chunk
        return data

    try:
        with socket.create_connection((address, port), timeout=5) as sock:
            sock.sendall(bytes.fromhex("030000130ee000000000000100080003000000"))
            header = read(sock, 4)
            size = int.from_bytes(header[2:], "big")
            if header[:2] != b"\x03\x00" or not 19 <= size <= 4096:
                raise ValueError("目标未返回有效的 RDP 协商")
            response = header + read(sock, size - 4)
            if (response[5] != 0xD0 or response[-8] != 2 or response[-6:-4] != b"\x08\x00"
                    or int.from_bytes(response[-4:], "little") not in {1, 2, 8}):
                raise ValueError("目标不支持 RDP TLS/NLA")
            # Certificate inspection only. Real gateway logins still require the saved pin.
            context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
            context.minimum_version = ssl.TLSVersion.TLSv1_2
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
            sock.settimeout(remaining())
            with context.wrap_socket(sock, server_hostname=address) as tls:
                certificate = tls.getpeercert(binary_form=True)
                if not certificate:
                    raise ValueError("目标未提供 RDP 证书")
                return "SHA256:" + hashlib.sha256(certificate).hexdigest()
    except (OSError, ValueError) as exc:
        reason = str(exc) if isinstance(exc, ValueError) else type(exc).__name__
        raise HTTPException(status_code=502, detail=f"无法获取 RDP 证书：{reason}") from exc


def test_rdp_connection(host):
    started = time.monotonic()
    fingerprint = probe_rdp_fingerprint(host.address, host.port)
    if not hmac.compare_digest(fingerprint.lower(), (host.host_key_fingerprint or "").lower()):
        result = CommandResult(1, "", "RDP 证书指纹不匹配，请核验目标机器后重新获取指纹")
    else:
        result = CommandResult(0, "RDP TLS/NLA 及证书校验通过；完整桌面登录仍需验证 Windows 凭据", "")
    return result, int(
        (time.monotonic() - started) * 1000
    )


def rdp_credential(host):
    credential = host.credential
    pin = (host.host_key_fingerprint or "").removeprefix("SHA256:").lower()
    if not credential or credential.auth_type != "password":
        raise HTTPException(status_code=400, detail="RDP 主机必须绑定密码凭据")
    password = decrypt_secret(credential.password_encrypted)
    if not password or not re.fullmatch(r"[0-9a-f]{64}", pin):
        raise HTTPException(status_code=400, detail="请配置 Windows 密码凭据及 RDP 证书 SHA256 指纹")
    domain, username = (credential.username.split("\\", 1) if "\\" in credential.username
                        else ("", credential.username))
    return {"address": validate_rdp_address(host.address), "port": host.port,
            "username": username, "domain": domain, "password": password, "fingerprint": pin}


@dataclass
class Relay:
    ip: str
    sockets: tuple
    created: float = field(default_factory=time.monotonic)
    uid: int = 0
    hid: int = 0
    stamp: str = ""
    actor_name: str = ""
    target: str = ""
    authorized: bool = False
    connected: bool = False
    ended: bool = False
    ntlm_requested: bool = False


class RDPGatewayService:
    def __init__(self):
        self.internal_secret = secrets.token_urlsafe(32)
        self._process = None
        self._listener = None
        self._config_dir = None
        self._lock = threading.RLock()
        self._sessions = {}
        self._ips = OrderedDict()
        self._active = 0
        self._tls_server = None
        self._tls_proxy = None

    @property
    def running(self):
        return self._listener is not None and self._process is not None and self._process.poll() is None

    def public_address(self):
        value = get_settings().rdp_gateway_public_address.strip()
        try:
            parsed = urlsplit(f"//{value}")
            if (not parsed.hostname or parsed.username or parsed.password or parsed.path
                    or parsed.query or parsed.fragment or any(c.isspace() for c in value)):
                raise ValueError()
            validate_rdp_address(parsed.hostname)
            if parsed.port == 0:
                raise ValueError()
            if parsed.port is None:
                value = f"{value}:{get_settings().rdp_gateway_port}"
        except (ValueError, HTTPException):
            raise HTTPException(status_code=503, detail="请配置 RDP_GATEWAY_PUBLIC_ADDRESS（域名:端口）")
        return value

    def issue_file(self, db, user, host, client_ip):
        if not get_settings().rdp_gateway_enabled or not self.running:
            raise HTTPException(status_code=503, detail="RDP 网关未运行")
        host = require_host_access(db, user, host.id, "connect")
        if host.host_type != "rdp" or not host.is_active:
            raise HTTPException(status_code=403, detail="RDP 主机不存在或已禁用")
        rdp_credential(host)
        # Host names and usernames cannot inject extra .rdp lines.
        login = f"{user.username}#{host.name}" if user.id > 0 else host.name
        if any(c in login for c in "\r\n\x00"):
            raise HTTPException(status_code=400, detail="用户名或主机名包含无效字符")
        lines = [f"full address:s:{self.public_address()}", f"username:s:{login}",
                 "gatewayusagemethod:i:0", f"enablecredsspsupport:i:{int(user.id > 0)}",
                 "negotiate security layer:i:1", "authentication level:i:1",
                 "prompt for credentials:i:1", "autoreconnection enabled:i:0",
                 "redirectclipboard:i:0", "redirectprinters:i:0", "redirectcomports:i:0",
                 "redirectsmartcards:i:0", "drivestoredirect:s:", "devicestoredirect:s:"]
        add_audit_log(db, host, user, "rdp_file_downloaded", "success", client_ip, target=rdp_target(host))
        return ("\r\n".join(lines) + "\r\n").encode("utf-16")

    def _principal(self, db, uid):
        if uid > 0:
            user = db.get(User, uid)
            if user and user.is_active:
                return user, user.password_hash
        elif uid < 0:
            key = db.get(ApiKey, -uid)
            if key and key.is_active and not key.is_expired():
                return User(id=uid, username=f"api_key_{key.id}", role="api_key", is_active=True), key.key
        raise HTTPException(status_code=403, detail="RDP 平台凭据已失效")

    def _stamp(self, host, platform_stamp):
        credential = host.credential
        parts = [platform_stamp, rdp_target(host), str(credential.id) if credential else "",
                 credential.username if credential else "", (credential.password_encrypted or "") if credential else "",
                 host.host_key_fingerprint or ""]
        return hashlib.sha256("\x00".join(parts).encode()).hexdigest()

    def authorize(self, db, connection_port, username, password, phase="login", domain=""):
        with self._lock:
            relay = self._sessions.get(connection_port)
            if not relay or relay.ended or time.monotonic() - relay.created >= SESSION_SECONDS:
                raise HTTPException(status_code=403, detail="RDP 连接已失效")
            if phase == "connected":
                if not relay.authorized or relay.connected:
                    raise HTTPException(status_code=403, detail="RDP 连接状态无效")
                user, host = self._validate(db, relay)
                relay.connected = True
                add_audit_log(db, host, user, "rdp_desktop_connected", "success", relay.ip, target=relay.target)
                return {}
            if relay.authorized or time.monotonic() - relay.created > 20:
                raise HTTPException(status_code=403, detail="RDP 认证已结束或超时")
            state = self._ips.get(relay.ip)
            if state and state["blocked"] > time.monotonic():
                raise HTTPException(status_code=403, detail="RDP 认证暂时受限")
            if phase == "ntlm":
                relay.ntlm_requested = True
                mode, login_name, host_name = parse_gateway_username(username)
                user = db.query(User).filter_by(username=login_name, is_active=True).first() if mode == "user" else None
                if (not user or not _authorize_gateway_identity(db, user, host_name, mode=mode,
                        host_type="rdp", permission="connect") or not ntlm_verifier(user)):
                    raise HTTPException(status_code=403, detail="NLA 凭据不可用，请先使用平台密码登录网页")
                # Return only the identity-specific NTLMv2 key to the local FreeRDP callback.
                identity = (username.upper() + domain).encode("utf-16-le")
                return {"ntlm_v2": hmac.new(bytes.fromhex(ntlm_verifier(user)), identity, "md5").hexdigest()}
            context = authenticate_gateway_resource(db, username, password, host_type="rdp", permission="connect")
            if not context:
                if state and not relay.ntlm_requested:
                    state["failures"] += 1
                    if state["failures"] >= 10:
                        state["blocked"] = time.monotonic() + 1800
                raise HTTPException(status_code=403, detail="平台认证或主机授权失败")
            host = db.get(ManagedHost, context.host_id)
            result = rdp_credential(host)
            user, platform_stamp = self._principal(db, context.user.id)
            relay.uid, relay.hid = user.id, host.id
            relay.stamp = self._stamp(host, platform_stamp)
            relay.actor_name, relay.target, relay.authorized = user.username, rdp_target(host), True
            add_audit_log(db, host, user, "rdp_gateway_authorized", "success", relay.ip, target=relay.target)
            return result

    def _validate(self, db, relay):
        user, platform_stamp = self._principal(db, relay.uid)
        host = require_host_access(db, user, relay.hid, "connect")
        if (host.host_type != "rdp" or not host.is_active or not host.credential
                or not hmac.compare_digest(relay.stamp, self._stamp(host, platform_stamp))):
            raise HTTPException(status_code=403, detail="RDP 主机或凭据已变更")
        return user, host

    def _admit(self, ip):
        now = time.monotonic()
        with self._lock:
            for key, state in list(self._ips.items()):
                if not state["active"] and now - state["since"] > 300 and state["blocked"] <= now:
                    del self._ips[key]
            state = self._ips.get(ip)
            if state is None:
                if len(self._ips) >= 4096:
                    return False
                state = self._ips[ip] = dict(since=now, attempts=0, failures=0, blocked=0, active=0)
            if now - state["since"] > 300:
                state.update(since=now, attempts=0, failures=0)
            state["attempts"] += 1
            if self._active >= 128 or state["active"] >= 8 or state["attempts"] > 60 or state["blocked"] > now:
                return False
            self._active += 1
            state["active"] += 1
            return True

    def _accept(self, listener, proxy_port):
        while self._listener is listener:
            try:
                client, address = listener.accept()
            except socket.timeout:
                continue
            except OSError:
                break
            ip = normalize_ip(address[0])
            if not self._admit(ip):
                client.close()
                continue
            threading.Thread(target=self._relay, args=(client, ip, proxy_port), daemon=True).start()

    @staticmethod
    def _tpkt(sock):
        def read(size):
            data = b""
            while len(data) < size:
                chunk = sock.recv(size - len(data))
                if not chunk:
                    raise OSError("Incomplete RDP negotiation")
                data += chunk
            return data
        header = read(4)
        size = int.from_bytes(header[2:], "big")
        if header[:2] != b"\x03\x00" or not 11 <= size <= 4096:
            raise OSError("Invalid RDP negotiation length")
        return header + read(size - 4)

    def _relay(self, client, ip, proxy_port):
        upstream = None
        relay = None
        port = None
        stage = "connect"
        try:
            upstream = socket.create_connection(("127.0.0.1", proxy_port), timeout=3)
            port = upstream.getsockname()[1]
            relay = Relay(ip=ip, sockets=(client, upstream))
            with self._lock:
                self._sessions[port] = relay
            for sock in relay.sockets:
                sock.settimeout(3)
                # RDP input and frame acknowledgements must not wait for Nagle.
                sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            # FreeRDP 3.15 sends only the leaf certificate. Terminate public TLS
            # here with the complete configured chain; authenticate the private
            # loopback TLS hop against that exact configured certificate.
            request = self._tpkt(client)
            if request[5] != 0xE0:
                return
            upstream.sendall(request)
            response = self._tpkt(upstream)
            if response[5] != 0xD0 or response[-8] != 2 or int.from_bytes(response[-4:], "little") not in {1, 2, 8}:
                return
            client.sendall(response)
            hostname = urlsplit("//" + self.public_address()).hostname
            stage = "upstream_tls"
            upstream = self._tls_proxy.wrap_socket(upstream, server_hostname=hostname)
            stage = "client_tls"
            client = self._tls_server.wrap_socket(client, server_side=True)
            stage = "relay"
            relay.sockets = (client, upstream)
            check_at = time.monotonic()
            while not relay.ended and self.running:
                now = time.monotonic()
                if now - relay.created >= (SESSION_SECONDS if relay.authorized else 20):
                    break
                if relay.authorized and now >= check_at:
                    with SessionLocal() as db:
                        self._validate(db, relay)
                    check_at = now + 15
                pending = [sock for sock in relay.sockets if sock.pending()]
                readable, _, _ = select.select(relay.sockets, [], [], 0 if pending else 0.5)
                # Buffered graphics must not starve input or frame acknowledgements.
                ready = [sock for sock in relay.sockets if sock in pending or sock in readable]
                for source in ready:
                    # TLS control records can make select readable without any RDP
                    # bytes. Never block the opposite direction waiting for them.
                    try:
                        source.settimeout(0)
                        chunk = source.recv(65536)
                    except (ssl.SSLWantReadError, ssl.SSLWantWriteError):
                        continue
                    finally:
                        source.settimeout(3)
                    if not chunk:
                        return
                    (upstream if source is client else client).sendall(chunk)
        except (OSError, ValueError, HTTPException) as exc:
            logger.info("RDP connection closed: stage=%s error=%s", stage, type(exc).__name__)
        except Exception:
            logger.error("RDP relay closed because authorization or transport failed")
        finally:
            with self._lock:
                if relay:
                    relay.ended = True
                    if relay.ntlm_requested and not relay.authorized:
                        state = self._ips[ip]
                        state["failures"] += 1
                        if state["failures"] >= 10:
                            state["blocked"] = time.monotonic() + 1800
                self._sessions.pop(port, None)
                self._active -= 1
                self._ips[ip]["active"] -= 1
            client.close()
            if upstream:
                upstream.close()
            if relay and relay.authorized:
                try:
                    with SessionLocal() as db:
                        host = db.get(ManagedHost, relay.hid)
                        if host:
                            actor = User(id=relay.uid, username=relay.actor_name, role="user")
                            add_audit_log(db, host, actor, "rdp_gateway_closed", "success", ip,
                                          target=relay.target, duration_ms=min(28800000, int((time.monotonic()-relay.created)*1000)))
                except Exception:
                    logger.error("RDP disconnect audit could not be written")

    def start(self):
        settings = get_settings()
        if not settings.rdp_gateway_enabled or self.running:
            return
        self.public_address()
        binary = shutil.which(settings.rdp_gateway_binary)
        if not binary:
            raise RuntimeError("找不到 freerdp-proxy3，请使用带 RDP 代理的项目镜像")
        for path in (settings.rdp_gateway_tls_cert_path, settings.rdp_gateway_tls_key_path):
            if not os.path.isfile(path):
                raise RuntimeError("RDP 网关 TLS 证书或私钥不存在")
        self._tls_server = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        self._tls_server.minimum_version = ssl.TLSVersion.TLSv1_2
        self._tls_server.load_cert_chain(settings.rdp_gateway_tls_cert_path, settings.rdp_gateway_tls_key_path)
        self._tls_proxy = ssl.create_default_context(cafile=settings.rdp_gateway_tls_cert_path)
        self._tls_proxy.minimum_version = ssl.TLSVersion.TLSv1_2
        self._tls_proxy.verify_flags |= ssl.VERIFY_X509_PARTIAL_CHAIN
        with socket.socket() as reservation:
            reservation.bind(("127.0.0.1", 0))
            proxy_port = reservation.getsockname()[1]
        self._config_dir = tempfile.TemporaryDirectory(prefix="frp-rdp-")
        config_path = os.path.join(self._config_dir.name, "proxy.ini")
        config = f"""[Server]
Host=127.0.0.1
Port={proxy_port}
[Target]
FixedTarget=false
Host=unused.invalid
Port=3389
[Channels]
GFX=true
DisplayControl=true
Clipboard=false
AudioInput=false
AudioOutput=false
DeviceRedirection=false
VideoRedirection=false
CameraRedirection=false
RemoteApp=false
PassthroughIsBlacklist=false
Passthrough=
Intercept=
[Input]
Keyboard=true
Mouse=true
Multitouch=false
[Security]
ServerTlsSecurity=true
ServerNlaSecurity=true
ServerRdpSecurity=false
ClientNlaSecurity=true
ClientTlsSecurity=false
ClientRdpSecurity=false
ClientAllowFallbackToTls=false
[Plugins]
Modules=frpagent
Required=frpagent
[Certificates]
CertificateFile={os.path.abspath(settings.rdp_gateway_tls_cert_path)}
PrivateKeyFile={os.path.abspath(settings.rdp_gateway_tls_key_path)}
"""
        with open(config_path, "w", encoding="utf-8") as file:
            file.write(config)
        env = {**os.environ, "FRP_RDP_AUTH_URL": f"http://127.0.0.1:{settings.app_port}/api/managed-hosts/gateway/rdp/authorize",
               "FRP_RDP_INTERNAL_SECRET": self.internal_secret, "WLOG_LEVEL": "ERROR"}
        try:
            self._process = subprocess.Popen([binary, config_path], env=env, stdin=subprocess.DEVNULL)
            for _ in range(50):
                if self._process.poll() is not None:
                    raise RuntimeError("FreeRDP 代理启动失败（检查必需认证模块和 TLS 配置）")
                try:
                    with socket.create_connection(("127.0.0.1", proxy_port), timeout=0.1):
                        break
                except OSError:
                    time.sleep(0.1)
            else:
                raise RuntimeError("FreeRDP 代理启动超时")
            listener = socket.create_server((settings.rdp_gateway_host, settings.rdp_gateway_port))
            listener.settimeout(1)
            self._listener = listener
            threading.Thread(target=self._accept, args=(listener, proxy_port), daemon=True).start()
            logger.info("RDP 平台认证网关启动于 %s:%s", settings.rdp_gateway_host, settings.rdp_gateway_port)
        except Exception:
            self.stop()
            raise

    def stop(self):
        listener, self._listener = self._listener, None
        if listener:
            listener.close()
        with self._lock:
            for relay in self._sessions.values():
                relay.ended = True
                for sock in relay.sockets:
                    try:
                        sock.shutdown(socket.SHUT_RDWR)
                    except OSError:
                        pass
        if self._process and self._process.poll() is None:
            self._process.terminate()
            try:
                self._process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._process.kill()
                self._process.wait()
        self._process = None
        if self._config_dir:
            self._config_dir.cleanup()
            self._config_dir = None


rdp_gateway_service = RDPGatewayService()
