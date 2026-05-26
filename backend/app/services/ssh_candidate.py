"""SSH 升级候选代理判定"""
from app.models.proxy import Proxy


def is_ssh_candidate(proxy: Proxy) -> bool:
    return (
        proxy.proxy_type == "tcp"
        and proxy.local_port == 22
        and proxy.remote_port is not None
        and proxy.status == "online"
    )


def ssh_target_host(proxy: Proxy) -> str:
    if proxy.frps_server is None:
        raise ValueError("代理未关联 frps 服务器")
    return proxy.frps_server.server_addr


def ssh_target_port(proxy: Proxy) -> int:
    return int(proxy.remote_port)
