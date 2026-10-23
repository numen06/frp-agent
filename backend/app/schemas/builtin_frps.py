"""内置 frps 的基础、安全、插件及原始 TOML 配置。"""
import ipaddress
import re
from typing import Optional, Literal, Annotated
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


PluginOperation = Literal["Login", "NewProxy", "CloseProxy", "Ping", "NewWorkConn", "NewUserConn"]
Port = Annotated[int, Field(ge=1, le=65535)]


class FrpsHttpPlugin(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    addr: str = Field(..., min_length=1, max_length=255)
    path: str = Field("/handler", min_length=1, max_length=255, pattern=r"^/")
    ops: list[PluginOperation] = Field(..., min_length=1)
    tls_verify: bool = True

    @field_validator("addr")
    @classmethod
    def validate_addr(cls, value):
        try:
            url = urlsplit(value if "://" in value else "http://" + value)
            if url.scheme not in {"http", "https"} or not url.hostname or not url.port or url.username or url.password or url.path not in {"", "/"} or url.query or url.fragment:
                raise ValueError()
        except ValueError:
            raise ValueError("插件地址使用主机名:端口或 HTTP(S) 地址，接口路径另行填写")
        return value


class BuiltinFrpsUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled: bool = False
    public_addr: str = Field("", max_length=255)
    bind_port: int = Field(7000, ge=1, le=65535)
    dashboard_port: int = Field(7500, ge=1, le=65535)
    proxy_port_start: int = Field(6000, ge=1, le=65535)
    proxy_port_end: int = Field(6099, ge=1, le=65535)
    vhost_http_port: int = Field(0, ge=0, le=65535)
    vhost_https_port: int = Field(0, ge=0, le=65535)
    tls_force: bool = True
    bind_addr: str = "0.0.0.0"
    proxy_bind_addr: str = ""
    kcp_bind_port: int = Field(0, ge=0, le=65535)
    quic_bind_port: int = Field(0, ge=0, le=65535)
    tls_cert_file: str = Field("", max_length=1024)
    tls_key_file: str = Field("", max_length=1024)
    tls_trusted_ca_file: str = Field("", max_length=1024)
    auth_additional_scopes: list[Literal["HeartBeats", "NewWorkConns"]] = Field(default_factory=list)
    max_ports_per_client: int = Field(0, ge=0, le=65535)
    log_level: Literal["trace", "debug", "info", "warn", "error"] = "info"
    http_plugins: list[FrpsHttpPlugin] = Field(default_factory=list, max_length=100)
    allowed_port_ranges: Optional[list[tuple[Port, Port]]] = Field(None, min_length=1, max_length=100)
    auth_token: Optional[str] = Field(None, min_length=16, max_length=255)

    @field_validator("bind_addr", "proxy_bind_addr")
    @classmethod
    def validate_bind_address(cls, value):
        return str(ipaddress.ip_address(value)) if value else value

    @field_validator("tls_cert_file", "tls_key_file", "tls_trusted_ca_file")
    @classmethod
    def validate_file_path(cls, value):
        if any(ord(char) < 32 for char in value):
            raise ValueError("证书文件路径不能包含控制字符")
        return value

    @field_validator("auth_token")
    @classmethod
    def validate_token(cls, value):
        if value is not None and (value != value.strip() or any(ord(char) < 32 or ord(char) == 127 for char in value)):
            raise ValueError("Token 不能包含控制字符或首尾空白")
        return value

    @field_validator("public_addr")
    @classmethod
    def validate_address(cls, value):
        value = value.strip()
        if not value:
            return value
        try:
            return str(ipaddress.ip_address(value))
        except ValueError:
            if not re.fullmatch(r"[A-Za-z0-9](?:[A-Za-z0-9.-]*[A-Za-z0-9])?", value):
                raise ValueError("填写公网 IP 或域名，不含协议、路径或端口")
            if any(not label or len(label) > 63 or label.startswith("-") or label.endswith("-") for label in value.split(".")):
                raise ValueError("公网域名无效")
        return value

    @model_validator(mode="after")
    def validate_ports(self):
        if self.enabled and not self.public_addr:
            raise ValueError("启用内置 FRP 时需要填写客户端可访问的公网 IP 或域名")
        if self.proxy_port_start > self.proxy_port_end:
            raise ValueError("代理端口范围起始值不能大于结束值")
        ports = [self.bind_port, self.dashboard_port, self.vhost_http_port, self.vhost_https_port]
        ports = [port for port in ports if port]
        if len(ports) != len(set(ports)):
            raise ValueError("FRP 监听端口不能重复")
        ranges = self.allowed_port_ranges or [(self.proxy_port_start, self.proxy_port_end)]
        if any(start > end for start, end in ranges):
            raise ValueError("允许端口范围起始值不能大于结束值")
        if (min(start for start, _ in ranges), max(end for _, end in ranges)) != (self.proxy_port_start, self.proxy_port_end):
            ranges = [(self.proxy_port_start, self.proxy_port_end)]
        if any(start <= port <= end for start, end in ranges for port in ports):
            raise ValueError("代理端口范围不能包含 FRP 控制、管理或 HTTP/HTTPS 端口")
        if bool(self.tls_cert_file) != bool(self.tls_key_file):
            raise ValueError("TLS 证书和私钥路径必须同时填写")
        if len({plugin.name for plugin in self.http_plugins}) != len(self.http_plugins):
            raise ValueError("插件名称不能重复")
        udp_ports = [port for port in (self.kcp_bind_port, self.quic_bind_port) if port]
        if len(udp_ports) != len(set(udp_ports)) or any(port in {self.dashboard_port, self.vhost_http_port, self.vhost_https_port} for port in udp_ports):
            raise ValueError("KCP/QUIC 端口不能相互重复或占用管理、HTTP/HTTPS 端口")
        return self


class BuiltinFrpsRawUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    enabled: bool = False
    public_addr: str = Field("", max_length=255)
    content: str = Field(..., min_length=1, max_length=131072)
    revision: Optional[str] = Field(None, max_length=64)

    @field_validator("public_addr")
    @classmethod
    def validate_address(cls, value):
        return BuiltinFrpsUpdate.validate_address(value)
