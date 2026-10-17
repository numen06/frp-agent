"""FRP 版本采集与聚合"""
from collections import Counter
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from app.frps_client import FrpsClient
from app.models.frps_server import FrpsServer
from app.models.proxy import Proxy


async def refresh_server_version(
    db: Session,
    server: FrpsServer,
    client: Optional[FrpsClient] = None,
) -> Tuple[Optional[str], str]:
    """拉取并保存 frps 服务端版本

    Returns:
        (version, message)
    """
    if client is None:
        client = FrpsClient(server)

    now = datetime.utcnow()
    server.last_version_check_time = now

    version = await client.get_server_version()
    if version:
        server.server_version = version
        server.last_version_check_message = "获取成功"
        message = "获取成功"
    else:
        server.last_version_check_message = "连接成功，但未获取到 frps 版本"
        message = server.last_version_check_message

    db.commit()
    return version, message


def apply_proxy_version(db_proxy: Proxy, proxy_info: dict) -> None:
    """将解析后的 client_version 写入代理（缺失时置空）"""
    db_proxy.client_version = proxy_info.get("client_version")


def aggregate_client_versions(db: Session, server_id: int) -> dict:
    """聚合指定服务器下 frpc 版本分布"""
    proxies = db.query(Proxy).filter(Proxy.frps_server_id == server_id).all()
    total = len(proxies)
    known = [p for p in proxies if p.client_version]
    unknown_count = total - len(known)

    counter = Counter(p.client_version for p in known)
    versions: List[dict] = [
        {"client_version": ver, "count": count}
        for ver, count in sorted(counter.items(), key=lambda x: (-x[1], x[0]))
    ]

    return {
        "total_proxies": total,
        "known_version_count": len(known),
        "unknown_version_count": unknown_count,
        "versions": versions,
    }


def build_frp_version_response(db: Session, server: FrpsServer) -> dict:
    """构建 FRP 版本查询响应"""
    return {
        "success": True,
        "server": {
            "id": server.id,
            "name": server.name,
            "server_version": server.server_version,
            "last_version_check_time": server.last_version_check_time,
            "last_version_check_message": server.last_version_check_message,
        },
        "clients": aggregate_client_versions(db, server.id),
    }
