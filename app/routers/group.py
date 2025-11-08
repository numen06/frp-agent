"""代理分组管理路由"""
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy.orm import Session
from sqlalchemy import func, case
from pydantic import BaseModel

from app.database import get_db
from app.auth import get_current_user
from app.models.user import User
from app.models.proxy import Proxy
from app.models.frps_server import FrpsServer

router = APIRouter(prefix="/api/groups", tags=["分组管理"])


class UpdateProxyGroupRequest(BaseModel):
    """更新代理分组请求"""
    proxy_id: int
    group_name: str


class BatchUpdateGroupRequest(BaseModel):
    """批量更新分组请求"""
    proxy_ids: List[int]
    group_name: str


@router.get("")
def get_groups(
    frps_server_id: Optional[int] = Query(None, description="按服务器ID过滤"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取代理分组列表及统计信息
    
    返回所有分组及其代理数量、在线数量等统计信息
    """
    query = db.query(
        Proxy.group_name,
        Proxy.frps_server_id,
        func.count(Proxy.id).label("total_count"),
        func.sum(case((Proxy.status == "online", 1), else_=0)).label("online_count"),
        func.sum(case((Proxy.status == "offline", 1), else_=0)).label("offline_count")
    ).filter(
        Proxy.group_name.isnot(None),
        Proxy.group_name != ""
    ).group_by(Proxy.group_name, Proxy.frps_server_id)
    
    if frps_server_id:
        query = query.filter(Proxy.frps_server_id == frps_server_id)
    
    results = query.all()
    
    # 获取服务器信息
    server_map = {}
    if results:
        server_ids = list(set([r.frps_server_id for r in results]))
        servers = db.query(FrpsServer).filter(FrpsServer.id.in_(server_ids)).all()
        server_map = {s.id: s.name for s in servers}
    
    groups = []
    for result in results:
        groups.append({
            "group_name": result.group_name,
            "frps_server_id": result.frps_server_id,
            "frps_server_name": server_map.get(result.frps_server_id, "未知"),
            "total_count": result.total_count,
            "online_count": result.online_count,
            "offline_count": result.offline_count
        })
    
    return {
        "groups": groups,
        "total_groups": len(groups)
    }


@router.get("/{group_name}/proxies")
def get_group_proxies(
    group_name: str,
    frps_server_id: Optional[int] = Query(None, description="按服务器ID过滤"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取指定分组的所有代理"""
    query = db.query(Proxy).filter(Proxy.group_name == group_name)
    
    if frps_server_id:
        query = query.filter(Proxy.frps_server_id == frps_server_id)
    
    proxies = query.all()
    
    return {
        "group_name": group_name,
        "proxy_count": len(proxies),
        "proxies": [
            {
                "id": p.id,
                "name": p.name,
                "proxy_type": p.proxy_type,
                "remote_port": p.remote_port,
                "local_ip": p.local_ip,
                "local_port": p.local_port,
                "status": p.status,
                "frps_server_id": p.frps_server_id
            }
            for p in proxies
        ]
    }


@router.get("/{group_name}/summary")
def get_group_summary(
    group_name: str,
    frps_server_id: Optional[int] = Query(None, description="按服务器ID过滤"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取分组的详细统计信息"""
    query = db.query(Proxy).filter(Proxy.group_name == group_name)
    
    if frps_server_id:
        query = query.filter(Proxy.frps_server_id == frps_server_id)
    
    proxies = query.all()
    
    if not proxies:
        raise HTTPException(status_code=404, detail=f"分组 '{group_name}' 不存在")
    
    # 按类型统计
    type_stats = {}
    for proxy in proxies:
        ptype = proxy.proxy_type
        if ptype not in type_stats:
            type_stats[ptype] = {"total": 0, "online": 0, "offline": 0}
        type_stats[ptype]["total"] += 1
        if proxy.status == "online":
            type_stats[ptype]["online"] += 1
        else:
            type_stats[ptype]["offline"] += 1
    
    # 端口范围
    ports = [p.remote_port for p in proxies if p.remote_port]
    port_range = None
    if ports:
        port_range = {
            "min": min(ports),
            "max": max(ports),
            "count": len(ports)
        }
    
    return {
        "group_name": group_name,
        "total_proxies": len(proxies),
        "online_proxies": sum(1 for p in proxies if p.status == "online"),
        "offline_proxies": sum(1 for p in proxies if p.status == "offline"),
        "type_statistics": type_stats,
        "port_range": port_range,
        "servers": list(set([p.frps_server_id for p in proxies]))
    }


@router.put("/proxy/update")
def update_proxy_group(
    request: UpdateProxyGroupRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """手动更新单个代理的分组
    
    管理员可以手动调整代理的分组归属
    """
    proxy = db.query(Proxy).filter(Proxy.id == request.proxy_id).first()
    if not proxy:
        raise HTTPException(status_code=404, detail="代理不存在")
    
    old_group = proxy.group_name
    proxy.group_name = request.group_name if request.group_name else "其他"
    
    db.commit()
    db.refresh(proxy)
    
    return {
        "success": True,
        "message": f"代理 {proxy.name} 的分组已从 '{old_group}' 更新为 '{proxy.group_name}'",
        "proxy": {
            "id": proxy.id,
            "name": proxy.name,
            "old_group": old_group,
            "new_group": proxy.group_name
        }
    }


@router.put("/batch-update")
def batch_update_group(
    request: BatchUpdateGroupRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """批量更新代理分组
    
    管理员可以批量调整多个代理的分组
    """
    if not request.proxy_ids:
        raise HTTPException(status_code=400, detail="未选择任何代理")
    
    proxies = db.query(Proxy).filter(Proxy.id.in_(request.proxy_ids)).all()
    
    if not proxies:
        raise HTTPException(status_code=404, detail="未找到指定的代理")
    
    group_name = request.group_name if request.group_name else "其他"
    updated_count = 0
    
    for proxy in proxies:
        proxy.group_name = group_name
        updated_count += 1
    
    db.commit()
    
    return {
        "success": True,
        "message": f"已将 {updated_count} 个代理更新到分组 '{group_name}'",
        "updated_count": updated_count,
        "group_name": group_name
    }


@router.post("/rename")
def rename_group(
    old_name: str = Body(...),
    new_name: str = Body(...),
    frps_server_id: Optional[int] = Body(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """重命名分组
    
    将指定分组的所有代理更新到新分组名称
    """
    if not new_name:
        raise HTTPException(status_code=400, detail="新分组名称不能为空")
    
    query = db.query(Proxy).filter(Proxy.group_name == old_name)
    
    if frps_server_id:
        query = query.filter(Proxy.frps_server_id == frps_server_id)
    
    proxies = query.all()
    
    if not proxies:
        raise HTTPException(status_code=404, detail=f"分组 '{old_name}' 不存在或没有代理")
    
    for proxy in proxies:
        proxy.group_name = new_name
    
    db.commit()
    
    return {
        "success": True,
        "message": f"分组 '{old_name}' 已重命名为 '{new_name}'",
        "updated_count": len(proxies),
        "old_name": old_name,
        "new_name": new_name
    }


@router.post("/auto-analyze")
def auto_analyze_groups(
    frps_server_id: int = Body(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """自动分析并更新代理分组
    
    从代理名称中智能分析分组，并更新那些分组为"其他"或需要重新分析的代理
    """
    # 获取指定服务器的所有代理
    proxies = db.query(Proxy).filter(
        Proxy.frps_server_id == frps_server_id
    ).all()
    
    if not proxies:
        raise HTTPException(status_code=404, detail="未找到任何代理")
    
    # 统计信息
    updated_count = 0
    new_groups = set()
    analysis_result = {
        "total": len(proxies),
        "updated": 0,
        "unchanged": 0,
        "groups_found": {},
        "details": []
    }
    
    # 分析每个代理
    for proxy in proxies:
        old_group = proxy.group_name
        # 重新解析分组
        new_group = Proxy.parse_group_name(proxy.name)
        
        # 如果分组发生变化，更新
        if old_group != new_group:
            proxy.group_name = new_group
            updated_count += 1
            
            # 记录新发现的分组
            if new_group != "其他" and new_group not in new_groups:
                new_groups.add(new_group)
            
            analysis_result["details"].append({
                "proxy_name": proxy.name,
                "old_group": old_group,
                "new_group": new_group
            })
        
        # 统计分组中的代理数
        if new_group not in analysis_result["groups_found"]:
            analysis_result["groups_found"][new_group] = 0
        analysis_result["groups_found"][new_group] += 1
    
    analysis_result["updated"] = updated_count
    analysis_result["unchanged"] = len(proxies) - updated_count
    analysis_result["new_groups"] = list(new_groups)
    
    db.commit()
    
    return {
        "success": True,
        "message": f"分析完成，更新了 {updated_count} 个代理的分组",
        "analysis": analysis_result
    }

