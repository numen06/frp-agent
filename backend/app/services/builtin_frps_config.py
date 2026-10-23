"""基础表单与原始 TOML 共用配置：保留插件、高级字段和原始文件草稿。"""
from copy import deepcopy
import hashlib
import tomllib

import toml

from app.schemas.builtin_frps import BuiltinFrpsUpdate, FrpsHttpPlugin

FIELD_PATHS = {
    "bind_addr": ("bindAddr",), "bind_port": ("bindPort",),
    "proxy_bind_addr": ("proxyBindAddr",), "kcp_bind_port": ("kcpBindPort",),
    "quic_bind_port": ("quicBindPort",), "vhost_http_port": ("vhostHTTPPort",),
    "vhost_https_port": ("vhostHTTPSPort",), "dashboard_port": ("webServer", "port"),
    "tls_force": ("transport", "tls", "force"), "tls_cert_file": ("transport", "tls", "certFile"),
    "tls_key_file": ("transport", "tls", "keyFile"), "tls_trusted_ca_file": ("transport", "tls", "trustedCaFile"),
    "auth_additional_scopes": ("auth", "additionalScopes"),
    "max_ports_per_client": ("maxPortsPerClient",), "log_level": ("log", "level"),
}


def parse_document(content):
    try:
        return tomllib.loads(content)
    except tomllib.TOMLDecodeError as exc:
        raise ValueError(f"TOML 配置格式错误：{exc}") from exc


def at(document, path, default=None):
    value = document
    for key in path:
        if not isinstance(value, dict) or key not in value:
            return default
        value = value[key]
    return value


def put(document, path, value):
    target = document
    for key in path[:-1]:
        target = target.setdefault(key, {})
    target[path[-1]] = value


def allowed_ranges(document):
    entries = document.get("allowPorts")
    if not isinstance(entries, list) or not 1 <= len(entries) <= 100:
        raise ValueError("请在 allowPorts 中明确配置允许的代理端口（最多 100 段）")
    ranges = []
    for entry in entries:
        if not isinstance(entry, dict):
            raise ValueError("allowPorts 项必须为 single 或 start/end 对象")
        start, end = (entry["single"], entry["single"]) if entry.get("single") else (entry.get("start"), entry.get("end"))
        if type(start) is not int or type(end) is not int or not 1 <= start <= end <= 65535:
            raise ValueError("allowPorts 端口必须在 1–65535 范围内，且起始值不大于结束值")
        ranges.append((start, end))
    return sorted(ranges)


def plugin_form(plugin):
    return {"name": plugin.get("name"), "addr": plugin.get("addr"), "path": plugin.get("path", "/handler"),
            "ops": plugin.get("ops", []), "tls_verify": plugin.get("tlsVerify", False)}


def form_from_document(document):
    defaults = BuiltinFrpsUpdate().model_dump()
    defaults["tls_force"] = False  # Native frps default when absent from an edited file.
    plugins = document.get("httpPlugins", [])
    if not isinstance(plugins, list) or not all(isinstance(plugin, dict) for plugin in plugins):
        raise ValueError("httpPlugins 必须为 [[httpPlugins]] 配置数组")
    values = {key: at(document, path, defaults[key]) for key, path in FIELD_PATHS.items()}
    ranges = allowed_ranges(document)
    values.update(proxy_port_start=min(start for start, _ in ranges), proxy_port_end=max(end for _, end in ranges),
                  allowed_port_ranges=ranges, auth_token=at(document, ("auth", "token")),
                  http_plugins=[plugin_form(plugin) for plugin in plugins])
    # frps automatically forces TLS when a client CA is configured.
    if values["tls_trusted_ca_file"]:
        values["tls_force"] = True
    return values


def validate_document(content, enabled=False, public_addr=""):
    document = parse_document(content)
    if at(document, ("auth", "method"), "token") != "token" or at(document, ("auth", "tokenSource")):
        raise ValueError("平台自动交付客户端配置需要 auth.method = 'token' 和内联 auth.token")
    web = document.get("webServer", {})
    if not isinstance(web, dict) or web.get("addr") != "127.0.0.1" or web.get("tls"):
        raise ValueError("平台内部管理接口必须保持 webServer.addr = '127.0.0.1'，使用内部 HTTP 连接")
    if type(web.get("port")) is not int or not 1 <= web["port"] <= 65535:
        raise ValueError("请保留有效的 webServer.port 供平台内部管理使用")
    if not isinstance(web.get("user"), str) or not 1 <= len(web["user"]) <= 100:
        raise ValueError("webServer.user 必须为 1–100 个字符")
    if not isinstance(web.get("password"), str) or not 1 <= len(web["password"]) <= 255:
        raise ValueError("webServer.password 必须为 1–255 个字符；建议使用系统自动生成的密码")
    token = at(document, ("auth", "token"))
    if not isinstance(token, str) or not 1 <= len(token) <= 255:
        raise ValueError("auth.token 必须为 1–255 个字符；可使用系统自动生成的 Token")
    BuiltinFrpsUpdate.validate_token(token)
    # Raw imports retain legacy credentials so existing clients can reconnect.
    # Basic form changes still require new tokens to contain at least 16 characters.
    values = form_from_document(document)
    values.pop("auth_token")
    form = BuiltinFrpsUpdate(**values, enabled=enabled, public_addr=public_addr)
    return {**form.model_dump(), "auth_token": token, "dashboard_username": web["user"], "dashboard_password": web["password"],
            "raw_config": content, "_raw_exact": True}


def render_config(config):
    original = config.get("raw_config")
    if original and config.get("_raw_exact"):
        return original
    document = parse_document(original) if original else {
        "auth": {"method": "token"}, "webServer": {"addr": "127.0.0.1", "pprofEnable": False},
        "enablePrometheus": True, "detailedErrorsToClient": False,
        "log": {"to": "console", "disablePrintColor": True},
    }
    before = deepcopy(document)
    for key, path in FIELD_PATHS.items():
        value = config.get(key, BuiltinFrpsUpdate.model_fields[key].default)
        # Do not add absent default options to an existing raw document.
        if not original or at(document, path, value) != value:
            put(document, path, value)
    ranges = config.get("allowed_port_ranges")
    bounds = (config["proxy_port_start"], config["proxy_port_end"])
    if not ranges or (min(start for start, _ in ranges), max(end for _, end in ranges)) != bounds:
        ranges = [bounds]
    if not original or allowed_ranges(document) != sorted(map(tuple, ranges)):
        document["allowPorts"] = [{"start": start, "end": end} for start, end in ranges]
    put(document, ("auth", "token"), config["auth_token"])
    put(document, ("webServer", "password"), config["dashboard_password"])
    put(document, ("webServer", "user"), config.get("dashboard_username", "frp-agent"))
    plugins = [FrpsHttpPlugin.model_validate(plugin).model_dump() for plugin in config.get("http_plugins", [])]
    if plugins != [plugin_form(plugin) for plugin in document.get("httpPlugins", [])]:
        previous = {plugin["name"]: plugin for plugin in document.get("httpPlugins", [])}
        document["httpPlugins"] = [{**previous.get(plugin["name"], {}),
                                    **{key: value for key, value in plugin.items() if key != "tls_verify"},
                                    "tlsVerify": plugin["tls_verify"]} for plugin in plugins]
    if original and document == before:
        return original
    return toml.dumps(document)


def revision(content):
    return hashlib.sha256(content.encode("utf-8")).hexdigest()
