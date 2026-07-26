"""将受控 Docker Engine API 请求转发到 Portainer Endpoint 的 HTTPS 网关。"""
from __future__ import annotations

import base64
import ipaddress
import json
import logging
import os
import ssl
import threading
import time
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Optional
from urllib.parse import urlsplit

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID

from app.config import get_settings
from app.database import SessionLocal
from app.models.managed_host import ManagedHost
from app.services.host_access_service import add_audit_log, portainer_proxy_request
from app.services.ssh_gateway_service import (
    GatewayAuthContext,
    authenticate_gateway_resource,
)

logger = logging.getLogger(__name__)
MAX_REQUEST_BODY = 64 * 1024 * 1024
HOP_BY_HOP_HEADERS = {
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailers",
    "transfer-encoding",
    "upgrade",
    "content-length",
}


def _decode_basic_auth(value: str):
    if not value.lower().startswith("basic "):
        return None
    try:
        raw = base64.b64decode(value.split(" ", 1)[1], validate=True).decode("utf-8")
        return raw.split(":", 1)
    except Exception:
        return None


def _ensure_tls_certificate() -> tuple[str, str]:
    settings = get_settings()
    cert_path = os.path.abspath(settings.docker_gateway_tls_cert_path)
    key_path = os.path.abspath(settings.docker_gateway_tls_key_path)
    os.makedirs(os.path.dirname(cert_path), exist_ok=True)
    os.makedirs(os.path.dirname(key_path), exist_ok=True)
    if os.path.exists(cert_path) and os.path.exists(key_path):
        return cert_path, key_path

    private_key = rsa.generate_private_key(public_exponent=65537, key_size=3072)
    common_name = settings.docker_gateway_tls_common_name.strip() or "localhost"
    subject = issuer = x509.Name(
        [x509.NameAttribute(NameOID.COMMON_NAME, common_name)]
    )
    try:
        san_value = x509.IPAddress(ipaddress.ip_address(common_name))
    except ValueError:
        san_value = x509.DNSName(common_name)
    now = datetime.now(timezone.utc)
    certificate = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(private_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(minutes=5))
        .not_valid_after(now + timedelta(days=3650))
        .add_extension(x509.SubjectAlternativeName([san_value]), critical=False)
        .add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True)
        .sign(private_key, hashes.SHA256())
    )
    with open(key_path, "wb") as key_file:
        key_file.write(
            private_key.private_bytes(
                serialization.Encoding.PEM,
                serialization.PrivateFormat.TraditionalOpenSSL,
                serialization.NoEncryption(),
            )
        )
    with open(cert_path, "wb") as cert_file:
        cert_file.write(certificate.public_bytes(serialization.Encoding.PEM))
    for path in (key_path, cert_path):
        try:
            os.chmod(path, 0o600)
        except OSError:
            pass
    logger.warning(
        "已生成 Docker 网关自签名 TLS 证书（CN=%s）: %s",
        common_name,
        cert_path,
    )
    return cert_path, key_path


def docker_gateway_certificate_fingerprint() -> Optional[str]:
    settings = get_settings()
    cert_path = os.path.abspath(settings.docker_gateway_tls_cert_path)
    if not os.path.exists(cert_path):
        return None
    try:
        with open(cert_path, "rb") as cert_file:
            cert = x509.load_pem_x509_certificate(cert_file.read())
        digest = cert.fingerprint(hashes.SHA256())
        return "SHA256:" + base64.b64encode(digest).decode("ascii").rstrip("=")
    except Exception:
        return None


class DockerGatewayHandler(BaseHTTPRequestHandler):
    server_version = "frp-agent-docker-gateway/1.0"
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt, *args):
        logger.debug("Docker gateway %s - %s", self.client_address[0], fmt % args)

    def _send_json(self, status_code: int, payload: dict, authenticate=False):
        content = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        if authenticate:
            self.send_header("WWW-Authenticate", 'Basic realm="frp-agent Docker gateway"')
        self.end_headers()
        self.wfile.write(content)

    def _authenticate(self) -> Optional[GatewayAuthContext]:
        authorization = self.headers.get("Authorization", "")
        basic = _decode_basic_auth(authorization)
        if basic:
            gateway_username, password = basic
        elif authorization.lower().startswith("bearer "):
            gateway_username = self.headers.get("X-Host", "").strip()
            password = authorization.split(" ", 1)[1].strip()
        else:
            return None
        db = SessionLocal()
        try:
            return authenticate_gateway_resource(
                db,
                gateway_username,
                password,
                host_type="docker",
                permission="docker",
            )
        finally:
            db.close()

    def _handle(self):
        parsed = urlsplit(self.path)
        if parsed.path == "/_gateway/health":
            self._send_json(200, {"status": "healthy", "service": "docker-gateway"})
            return
        auth_context = self._authenticate()
        if not auth_context:
            self._send_json(401, {"detail": "认证失败或没有 Docker 主机权限"}, True)
            return

        content_length = int(self.headers.get("Content-Length", "0") or 0)
        if content_length > MAX_REQUEST_BODY:
            self._send_json(413, {"detail": "请求体超过 64 MiB 限制"})
            return
        body = self.rfile.read(content_length) if content_length else None
        docker_path = parsed.path or "/"
        proxy_path = (
            f"/api/endpoints/{auth_context.host_id}/docker{docker_path}"
        )

        # host_id 是本系统资源 ID，不是 Portainer Endpoint ID；重新读取主机后拼接。
        db = SessionLocal()
        started = time.monotonic()
        error_message = None
        status_code = 502
        response_started = False
        try:
            host = (
                db.query(ManagedHost)
                .filter(ManagedHost.id == auth_context.host_id)
                .first()
            )
            if not host or not host.docker_endpoint_id:
                raise ValueError("Docker 主机或 Portainer Endpoint 不存在")
            proxy_path = (
                f"/api/endpoints/{host.docker_endpoint_id}/docker{docker_path}"
            )
            if parsed.query:
                proxy_path += f"?{parsed.query}"
            forward_headers = {}
            for name in ("Content-Type", "Accept"):
                if self.headers.get(name):
                    forward_headers[name] = self.headers[name]
            status_code, response_headers, content, duration_ms = (
                portainer_proxy_request(
                    host,
                    self.command,
                    proxy_path,
                    timeout=get_settings().docker_gateway_request_timeout,
                    body=body,
                    request_headers=forward_headers,
                )
            )
            response_started = True
            self.send_response(status_code)
            for name, value in response_headers.items():
                if name.lower() not in HOP_BY_HOP_HEADERS:
                    self.send_header(name, value)
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            if self.command != "HEAD":
                self.wfile.write(content)
            add_audit_log(
                db,
                host,
                auth_context.user,
                "docker_gateway_request",
                "success" if 200 <= status_code < 400 else "failed",
                self.client_address[0],
                target=f"{self.command} {docker_path}",
                duration_ms=duration_ms,
                error=None if 200 <= status_code < 400 else f"HTTP {status_code}",
            )
        except Exception as exc:
            error_message = str(exc)
            logger.warning("Docker 网关请求失败: %s", exc)
            if not response_started and not self.wfile.closed:
                try:
                    self._send_json(502, {"detail": f"Docker 网关转发失败: {exc}"})
                except Exception:
                    pass
            if "host" in locals() and host:
                try:
                    add_audit_log(
                        db,
                        host,
                        auth_context.user,
                        "docker_gateway_request",
                        "failed",
                        self.client_address[0],
                        target=f"{self.command} {docker_path}",
                        duration_ms=int((time.monotonic() - started) * 1000),
                        error=error_message,
                    )
                except Exception:
                    logger.exception("写入 Docker 网关审计失败")
        finally:
            db.close()

    do_GET = _handle
    do_POST = _handle
    do_PUT = _handle
    do_PATCH = _handle
    do_DELETE = _handle
    do_HEAD = _handle
    do_OPTIONS = _handle


class DockerGatewayService:
    def __init__(self):
        self._server: Optional[ThreadingHTTPServer] = None
        self._thread: Optional[threading.Thread] = None

    @property
    def running(self):
        return bool(self._thread and self._thread.is_alive())

    def start(self):
        settings = get_settings()
        if not settings.docker_gateway_enabled or self.running:
            return
        cert_path, key_path = _ensure_tls_certificate()
        server = ThreadingHTTPServer(
            (settings.docker_gateway_host, settings.docker_gateway_port),
            DockerGatewayHandler,
        )
        server.daemon_threads = True
        tls_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        tls_context.minimum_version = ssl.TLSVersion.TLSv1_2
        tls_context.load_cert_chain(certfile=cert_path, keyfile=key_path)
        server.socket = tls_context.wrap_socket(server.socket, server_side=True)
        self._server = server
        self._thread = threading.Thread(
            target=server.serve_forever,
            kwargs={"poll_interval": 0.5},
            daemon=True,
            name="docker-gateway-listener",
        )
        self._thread.start()
        logger.info(
            "Docker HTTPS 网关已监听 %s:%s",
            settings.docker_gateway_host,
            settings.docker_gateway_port,
        )

    def stop(self):
        if self._server:
            self._server.shutdown()
            self._server.server_close()
            self._server = None
        if self._thread:
            self._thread.join(timeout=3)
            self._thread = None


docker_gateway_service = DockerGatewayService()
