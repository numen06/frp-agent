"""同步路由"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from datetime import datetime
import json

from app.database import get_db
from app.auth import get_current_user
from app.models.user import User
from app.models.frps_server import FrpsServer
from app.models.proxy import Proxy
from app.models.history import ProxyHistory
from app.frps_client import FrpsClient
from app.services.port_service import PortService

router = APIRouter(prefix="/api/sync", tags=["同步"])


@router.post("")
async def sync_proxies(
    frps_server_id: int = Query(..., description="frps 服务器 ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """手动同步代理状态"""
    # 获取服务器配置
    server = db.query(FrpsServer).filter(FrpsServer.id == frps_server_id).first()
    if not server:
        raise HTTPException(status_code=404, detail="服务器不存在")
    
    # 创建客户端
    client = FrpsClient(server)
    
    # 获取所有代理
    all_proxies_data = await client.get_all_proxies()
    
    # 合并所有类型的代理
    all_proxies = []
    for proxy_type, proxies in all_proxies_data.items():
        for proxy_data in proxies:
            parsed = client.parse_proxy_info(proxy_data)
            parsed["proxy_type"] = proxy_type
            all_proxies.append(parsed)
    
    # 更新数据库中的代理状态
    updated_count = 0
    new_count = 0
    offline_count = 0
    
    # 获取数据库中的所有代理
    db_proxies = db.query(Proxy).filter(Proxy.frps_server_id == frps_server_id).all()
    db_proxy_map = {proxy.name: proxy for proxy in db_proxies}
    
    # 更新或创建代理
    active_proxy_names = set()
    for proxy_info in all_proxies:
        proxy_name = proxy_info["name"]
        active_proxy_names.add(proxy_name)
        
        if proxy_name in db_proxy_map:
            # 更新现有代理
            db_proxy = db_proxy_map[proxy_name]
            old_status = db_proxy.status
            db_proxy.status = proxy_info["status"]
            db_proxy.remote_port = proxy_info["remote_port"]
            
            # 如果状态改变，记录历史
            if old_status != proxy_info["status"]:
                history = ProxyHistory(
                    frps_server_id=frps_server_id,
                    proxy_name=proxy_name,
                    action=proxy_info["status"],
                    timestamp=datetime.utcnow(),
                    details=json.dumps(proxy_info)
                )
                db.add(history)
            
            updated_count += 1
        else:
            # 创建新代理
            new_proxy = Proxy(
                frps_server_id=frps_server_id,
                name=proxy_name,
                proxy_type=proxy_info["proxy_type"],
                remote_port=proxy_info["remote_port"],
                local_ip=proxy_info["local_ip"],
                local_port=0,  # 本地端口未知
                status=proxy_info["status"]
            )
            db.add(new_proxy)
            
            # 记录历史
            history = ProxyHistory(
                frps_server_id=frps_server_id,
                proxy_name=proxy_name,
                action="discovered",
                timestamp=datetime.utcnow(),
                details=json.dumps(proxy_info)
            )
            db.add(history)
            
            new_count += 1
    
    # 标记不在活跃列表中的代理为离线
    for proxy_name, db_proxy in db_proxy_map.items():
        if proxy_name not in active_proxy_names and db_proxy.status == "online":
            db_proxy.status = "offline"
            
            # 记录历史
            history = ProxyHistory(
                frps_server_id=frps_server_id,
                proxy_name=proxy_name,
                action="offline",
                timestamp=datetime.utcnow(),
                details=json.dumps({"reason": "not_found_in_sync"})
            )
            db.add(history)
            
            offline_count += 1
    
    # 检测冲突
    port_service = PortService(db)
    conflicts = port_service.detect_conflicts(frps_server_id, all_proxies)
    
    # 记录冲突
    for conflict in conflicts:
        history = ProxyHistory(
            frps_server_id=frps_server_id,
            proxy_name=conflict.get("proxy_name", "unknown"),
            action="conflict",
            timestamp=datetime.utcnow(),
            details=json.dumps(conflict)
        )
        db.add(history)
    
    db.commit()
    
    return {
        "success": True,
        "updated": updated_count,
        "new": new_count,
        "offline": offline_count,
        "conflicts": conflicts,
        "total_proxies": len(all_proxies)
    }


@router.get("/history")
def get_sync_history(
    frps_server_id: int = Query(..., description="frps 服务器 ID"),
    limit: int = Query(50, description="返回记录数量"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取同步历史记录"""
    histories = db.query(ProxyHistory).filter(
        ProxyHistory.frps_server_id == frps_server_id
    ).order_by(ProxyHistory.timestamp.desc()).limit(limit).all()
    
    return histories

