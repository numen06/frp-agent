"""代理分组管理路由"""
import json
import os
import shlex
from typing import List, Optional, Dict, Any
from urllib.parse import quote
from fastapi import APIRouter, Depends, HTTPException, Query, Body, Request, Form
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session
from sqlalchemy import func, case
from pydantic import BaseModel

from app.database import get_db
from app.auth import get_current_user, verify_api_key
from app.models.user import User
from app.models.proxy import Proxy
from app.models.frps_server import FrpsServer
from app.models.group import Group
from app.models.frp_package import FrpPackage
from app.models.port import PortAllocation
from app.services.port_service import PortService
from app.services.config_parser import ConfigParser
from app.script_templates import load_shell_template
from app.scheduler import sync_server
from app.schemas.ssh_upgrade import GroupSshUpgradeRequest, ClientUpgradeJobResponse
from app.models.ssh_credential import SshCredential
from app.services.ssh_upgrade_service import scan_group, upgrade_group

router = APIRouter(prefix="/api/groups", tags=["分组管理"])


class UpdateProxyGroupRequest(BaseModel):
    """更新代理分组请求"""
    proxy_id: int
    group_name: str


class BatchUpdateGroupRequest(BaseModel):
    """批量更新分组请求"""
    proxy_ids: List[int]
    group_name: str


class AutoAnalyzeRequest(BaseModel):
    """自动分析分组请求"""
    frps_server_id: int


class CreateGroupRequest(BaseModel):
    """创建分组请求"""
    group_name: str
    frps_server_id: int


class DeleteGroupRequest(BaseModel):
    """删除分组请求"""
    group_name: str
    frps_server_id: int
    reassign_group: Optional[str] = None  # 可选：将代理重新分配到的分组


class ImportConfigRequest(BaseModel):
    """导入配置请求"""
    frps_server_id: int
    group_name: str
    config_content: str
    config_format: str = "auto"  # auto, ini, toml
    overwrite: bool = True  # 是否覆盖已存在的同名代理（默认覆盖）


@router.get("/list")
def get_groups_list(
    frps_server_id: Optional[int] = Query(None, description="按服务器ID过滤"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取所有分组名称列表（用于下拉选择）
    
    返回所有分组的名称列表，包括：
    1. Group 表中已创建的分组
    2. Proxy 表中存在的分组（即使未在 Group 表中创建）
    """
    groups_set = set()
    
    # 1. 从 Group 表获取已创建的分组
    group_query = db.query(Group.name)
    if frps_server_id:
        group_query = group_query.filter(Group.frps_server_id == frps_server_id)
    
    created_groups = group_query.all()
    for group in created_groups:
        groups_set.add(group.name)
    
    # 2. 从 Proxy 表获取存在的分组
    proxy_query = db.query(Proxy.group_name).filter(
        Proxy.group_name.isnot(None),
        Proxy.group_name != ""
    ).distinct()
    
    if frps_server_id:
        proxy_query = proxy_query.filter(Proxy.frps_server_id == frps_server_id)
    
    proxy_groups = proxy_query.all()
    for group in proxy_groups:
        if group.group_name:
            groups_set.add(group.group_name)
    
    # 排序并返回
    groups_list = sorted(list(groups_set))
    
    return {
        "groups": groups_list,
        "total": len(groups_list)
    }


@router.get("")
def get_groups(
    frps_server_id: Optional[int] = Query(None, description="按服务器ID过滤"),
    search: Optional[str] = Query(None, description="搜索分组名称"),
    page: int = Query(1, ge=1, description="页码，从1开始"),
    page_size: int = Query(10, ge=1, le=100, description="每页数量"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取代理分组列表及统计信息（支持分页和搜索）
    
    返回所有分组及其代理数量、在线数量等统计信息
    合并 Group 表（已创建的空分组）和 Proxy 表（有代理的分组）的数据
    """
    groups_dict = {}
    
    # 1. 从 Group 表获取已创建的分组（包括空分组）
    group_query = db.query(Group)
    if frps_server_id:
        group_query = group_query.filter(Group.frps_server_id == frps_server_id)
    
    created_groups = group_query.all()
    for group in created_groups:
        groups_dict[f"{group.frps_server_id}_{group.name}"] = {
            "group_name": group.name,
            "frps_server_id": group.frps_server_id,
            "total_count": 0,
            "online_count": 0,
            "offline_count": 0
        }
    
    # 2. 从 Proxy 表统计代理数量（按 frps_server_id+name 去重，优先保留信息完整的记录）
    keep_ids_subq = (
        db.query(
            func.coalesce(
                func.max(case((Proxy.local_port > 0, Proxy.id))),
                func.max(Proxy.id),
            ).label("keep_id")
        )
        .group_by(Proxy.frps_server_id, Proxy.name)
        .subquery()
    )
    keep_id_col = keep_ids_subq.c.keep_id

    proxy_query = db.query(
        Proxy.group_name,
        Proxy.frps_server_id,
        func.count(Proxy.id).label("total_count"),
        func.sum(case((Proxy.status == "online", 1), else_=0)).label("online_count"),
        func.sum(case((Proxy.status == "offline", 1), else_=0)).label("offline_count")
    ).filter(
        Proxy.group_name.isnot(None),
        Proxy.group_name != "",
        Proxy.id.in_(db.query(keep_id_col)),
    ).group_by(Proxy.group_name, Proxy.frps_server_id)

    if frps_server_id:
        proxy_query = proxy_query.filter(Proxy.frps_server_id == frps_server_id)
    
    proxy_results = proxy_query.all()
    
    # 合并或添加代理统计数据
    for result in proxy_results:
        key = f"{result.frps_server_id}_{result.group_name}"
        if key in groups_dict:
            # 更新已存在的分组统计
            groups_dict[key]["total_count"] = result.total_count
            groups_dict[key]["online_count"] = result.online_count
            groups_dict[key]["offline_count"] = result.offline_count
        else:
            # 添加未在 Group 表中的分组（从代理中发现的）
            groups_dict[key] = {
                "group_name": result.group_name,
                "frps_server_id": result.frps_server_id,
                "total_count": result.total_count,
                "online_count": result.online_count,
                "offline_count": result.offline_count
            }
    
    # 获取服务器信息
    server_map = {}
    if groups_dict:
        server_ids = list(set([g["frps_server_id"] for g in groups_dict.values()]))
        servers = db.query(FrpsServer).filter(FrpsServer.id.in_(server_ids)).all()
        server_map = {s.id: s.name for s in servers}
    
    # 构建返回结果
    groups = []
    for group_data in groups_dict.values():
        groups.append({
            "group_name": group_data["group_name"],
            "frps_server_id": group_data["frps_server_id"],
            "frps_server_name": server_map.get(group_data["frps_server_id"], "未知"),
            "total_count": group_data["total_count"],
            "online_count": group_data["online_count"],
            "offline_count": group_data["offline_count"]
        })
    
    # 按分组名称排序
    groups.sort(key=lambda x: x["group_name"])
    
    # 搜索过滤
    if search:
        search_pattern = search.lower()
        groups = [g for g in groups if search_pattern in g["group_name"].lower()]
    
    # 计算总数
    total = len(groups)
    
    # 应用分页
    offset = (page - 1) * page_size
    paginated_groups = groups[offset:offset + page_size]
    
    return {
        "items": paginated_groups,
        "page": page,
        "page_size": page_size,
        "total": total
    }


@router.get("/{group_name}/proxies")
def get_group_proxies(
    group_name: str,
    frps_server_id: Optional[int] = Query(None, description="按服务器ID过滤"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取指定分组的所有代理（按 frps_server_id+name 去重，优先保留信息完整的记录）"""
    keep_ids_subq = (
        db.query(
            func.coalesce(
                func.max(case((Proxy.local_port > 0, Proxy.id))),
                func.max(Proxy.id),
            ).label("keep_id")
        )
        .group_by(Proxy.frps_server_id, Proxy.name)
        .subquery()
    )
    keep_id_col = keep_ids_subq.c.keep_id

    query = db.query(Proxy).filter(
        Proxy.group_name == group_name,
        Proxy.id.in_(db.query(keep_id_col)),
    )

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


@router.post("/create")
def create_group(
    request: CreateGroupRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """创建新分组
    
    在数据库中创建一个新的分组记录
    """
    group_name = request.group_name.strip()
    
    if not group_name:
        raise HTTPException(status_code=400, detail="分组名称不能为空")
    
    if group_name == "其他":
        raise HTTPException(status_code=400, detail="不能创建名为'其他'的分组")
    
    # 检查分组是否已存在
    existing = db.query(Group).filter(
        Group.frps_server_id == request.frps_server_id,
        Group.name == group_name
    ).first()
    
    if existing:
        raise HTTPException(status_code=400, detail=f"分组 '{group_name}' 已存在")
    
    # 创建分组记录
    new_group = Group(
        frps_server_id=request.frps_server_id,
        name=group_name
    )
    db.add(new_group)
    db.commit()
    db.refresh(new_group)
    
    return {
        "success": True,
        "message": f"分组 '{group_name}' 已创建",
        "group_name": group_name,
        "group_id": new_group.id
    }


@router.delete("/{group_name}")
def delete_group(
    group_name: str,
    frps_server_id: int = Query(..., description="frps 服务器 ID"),
    reassign_group: Optional[str] = Query(None, description="将代理重新分配到的分组"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """删除分组
    
    删除指定的分组。如果指定了 reassign_group，则将该分组的所有代理重新分配到新分组；
    否则将代理分配到"其他"分组。
    """
    if not group_name or group_name == "其他":
        raise HTTPException(status_code=400, detail="无效的分组名称")
    
    # 删除 Group 表中的记录
    group_record = db.query(Group).filter(
        Group.frps_server_id == frps_server_id,
        Group.name == group_name
    ).first()
    
    if group_record:
        db.delete(group_record)
    
    # 查找该分组的所有代理
    proxies = db.query(Proxy).filter(
        Proxy.frps_server_id == frps_server_id,
        Proxy.group_name == group_name
    ).all()
    
    # 确定重新分配的目标分组
    target_group = reassign_group if reassign_group else "其他"
    
    # 重新分配所有代理
    affected_count = 0
    for proxy in proxies:
        proxy.group_name = target_group
        affected_count += 1
    
    db.commit()
    
    message = f"已删除分组 '{group_name}'"
    if affected_count > 0:
        message += f"，{affected_count} 个代理已移动到分组 '{target_group}'"
    
    return {
        "success": True,
        "message": message,
        "deleted_group": group_name,
        "target_group": target_group if affected_count > 0 else None,
        "affected_count": affected_count
    }


@router.post("/auto-analyze")
def auto_analyze_groups(
    frps_server_id: int = Body(..., embed=True),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """自动分析并更新代理分组
    
    从代理名称中智能分析分组，仅对分组为"其他"或空的代理进行更新。
    不会覆盖已有的分组。
    """
    # 获取指定服务器的所有代理
    proxies = db.query(Proxy).filter(
        Proxy.frps_server_id == frps_server_id
    ).all()
    
    if not proxies:
        raise HTTPException(status_code=404, detail="未找到任何代理")
    
    # 统计信息
    updated_count = 0
    skipped_count = 0
    new_groups = set()
    analysis_result = {
        "total": len(proxies),
        "updated": 0,
        "skipped": 0,  # 已有分组的代理数
        "unchanged": 0,  # 分析后未变化的代理数
        "groups_found": {},
        "details": []
    }
    
    # 分析每个代理
    for proxy in proxies:
        old_group = proxy.group_name
        
        # 只对分组为空、None 或"其他"的代理进行自动分析
        if old_group and old_group != "其他":
            # 跳过已有明确分组的代理
            skipped_count += 1
            analysis_result["details"].append({
                "proxy_name": proxy.name,
                "old_group": old_group,
                "new_group": old_group,
                "action": "skipped",
                "reason": "已有分组，不覆盖"
            })
            
            # 统计分组中的代理数
            if old_group not in analysis_result["groups_found"]:
                analysis_result["groups_found"][old_group] = 0
            analysis_result["groups_found"][old_group] += 1
            continue
        
        # 自动解析分组
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
                "old_group": old_group or "(空)",
                "new_group": new_group,
                "action": "updated"
            })
        else:
            analysis_result["details"].append({
                "proxy_name": proxy.name,
                "old_group": old_group or "(空)",
                "new_group": new_group,
                "action": "unchanged"
            })
        
        # 统计分组中的代理数
        if new_group not in analysis_result["groups_found"]:
            analysis_result["groups_found"][new_group] = 0
        analysis_result["groups_found"][new_group] += 1
    
    analysis_result["updated"] = updated_count
    analysis_result["skipped"] = skipped_count
    analysis_result["unchanged"] = len(proxies) - updated_count - skipped_count
    analysis_result["new_groups"] = list(new_groups)
    
    # 确保数据持久化保存
    try:
        # 先刷新更改到数据库（但不提交事务）
        db.flush()
        # 提交事务，持久化保存所有更改
        db.commit()
    except Exception as e:
        # 如果保存失败，回滚所有更改
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"保存分组数据失败: {str(e)}"
        )
    
    return {
        "success": True,
        "message": f"分析完成，更新了 {updated_count} 个代理的分组，跳过 {skipped_count} 个已有分组的代理",
        "analysis": analysis_result
    }


@router.get("/{group_name}/check-defaults")
def check_default_proxies(
    group_name: str,
    frps_server_id: int = Query(..., description="frps 服务器 ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """检查分组需要添加哪些默认代理
    
    检查 docker, ssh, http 三个默认代理在该分组中是否存在
    """
    # 定义默认代理配置
    default_configs = [
        {
            "type": "docker",
            "name": f"{group_name}_docker",
            "proxy_type": "tcp",
            "local_port": 9000,
            "description": "Docker 管理面板"
        },
        {
            "type": "ssh",
            "name": f"{group_name}_ssh",
            "proxy_type": "tcp",
            "local_port": 22,
            "description": "SSH 远程终端"
        },
        {
            "type": "http",
            "name": f"{group_name}_http",
            "proxy_type": "tcp",
            "local_port": 80,
            "description": "HTTP Web 服务"
        }
    ]
    
    # 查询该分组下的所有代理名称
    existing_proxies = db.query(Proxy.name).filter(
        Proxy.frps_server_id == frps_server_id,
        Proxy.group_name == group_name
    ).all()
    existing_names = set([p.name for p in existing_proxies])
    
    # 检查哪些需要添加，哪些已存在
    needed = []
    existing = []
    
    for config in default_configs:
        if config["name"] in existing_names:
            existing.append(config["name"])
        else:
            needed.append(config)
    
    return {
        "group_name": group_name,
        "needed": needed,
        "existing": existing,
        "total": len(default_configs)
    }


@router.post("/{group_name}/generate-defaults")
def generate_default_proxies(
    group_name: str,
    frps_server_id: int = Query(..., description="frps 服务器 ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """为分组生成默认代理配置
    
    为指定分组添加 docker(9000), ssh(22), http(80) 三个常用代理
    不会覆盖已存在的同名代理
    """
    # 定义默认代理配置
    default_configs = [
        {
            "name": f"{group_name}_docker",
            "proxy_type": "tcp",
            "local_ip": "127.0.0.1",
            "local_port": 9000,
            "description": "Docker 管理面板"
        },
        {
            "name": f"{group_name}_ssh",
            "proxy_type": "tcp",
            "local_ip": "127.0.0.1",
            "local_port": 22,
            "description": "SSH 远程终端"
        },
        {
            "name": f"{group_name}_http",
            "proxy_type": "tcp",
            "local_ip": "127.0.0.1",
            "local_port": 80,
            "description": "HTTP Web 服务"
        }
    ]
    
    # 查询该分组下已存在的代理名称
    existing_proxies = db.query(Proxy).filter(
        Proxy.frps_server_id == frps_server_id,
        Proxy.group_name == group_name
    ).all()
    existing_names = set([p.name for p in existing_proxies])
    
    # 使用端口服务自动分配远端端口
    port_service = PortService(db)
    
    # 创建不存在的代理
    created_proxies = []
    skipped_names = []
    
    for config in default_configs:
        if config["name"] in existing_names:
            # 已存在，跳过
            skipped_names.append(config["name"])
            continue
        
        # 自动分配远端端口（端口范围会自动根据现有端口扩展）
        remote_port = port_service.get_next_available_port(frps_server_id, 6000, 7000)
        if remote_port is None:
            raise HTTPException(
                status_code=500,
                detail=f"无法为代理 {config['name']} 分配可用端口（端口范围已满）"
            )
        
        # 分配端口
        try:
            port_service.allocate_port(frps_server_id, remote_port, config["name"])
        except ValueError as e:
            raise HTTPException(status_code=500, detail=f"分配端口失败: {str(e)}")
        
        # 创建新代理
        new_proxy = Proxy(
            frps_server_id=frps_server_id,
            name=config["name"],
            group_name=group_name,
            proxy_type=config["proxy_type"],
            local_ip=config["local_ip"],
            local_port=config["local_port"],
            remote_port=remote_port,
            status="offline"
        )
        db.add(new_proxy)
        created_proxies.append({
            "name": new_proxy.name,
            "local_ip": new_proxy.local_ip,
            "local_port": new_proxy.local_port,
            "remote_port": new_proxy.remote_port,
            "description": config["description"]
        })
    
    db.commit()
    
    return {
        "success": True,
        "message": f"已为分组 '{group_name}' 创建 {len(created_proxies)} 个默认代理，跳过 {len(skipped_names)} 个已存在的代理",
        "group_name": group_name,
        "total": len(default_configs),
        "created": len(created_proxies),
        "skipped": len(skipped_names),
        "proxies": created_proxies,
        "skipped_names": skipped_names
    }


@router.post("/{group_name}/regenerate-ports")
def regenerate_group_ports(
    group_name: str,
    frps_server_id: int = Query(..., description="frps 服务器 ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """重新生成分组中所有代理的远端端口
    
    为分组中所有 TCP/UDP 类型的代理重新分配远端端口
    会释放旧端口并分配新端口
    """
    # 查询该分组下的所有代理
    proxies = db.query(Proxy).filter(
        Proxy.frps_server_id == frps_server_id,
        Proxy.group_name == group_name
    ).all()
    
    if not proxies:
        raise HTTPException(status_code=404, detail=f"分组 '{group_name}' 中没有代理")
    
    # 使用端口服务
    port_service = PortService(db)
    
    # 筛选出需要重新分配端口的代理（只处理 TCP/UDP 类型）
    proxies_to_regenerate = [p for p in proxies if p.proxy_type in ["tcp", "udp"]]
    
    if not proxies_to_regenerate:
        raise HTTPException(status_code=400, detail=f"分组 '{group_name}' 中没有需要重新分配端口的代理（TCP/UDP类型）")
    
    # 先收集所有旧端口信息
    old_ports_map = {p.name: p.remote_port for p in proxies_to_regenerate}
    
    # 查询当前服务器的最大端口号（排除正在重新分配的代理）
    proxy_names_to_exclude = [p.name for p in proxies_to_regenerate]
    
    # 查询所有其他代理的端口（排除正在重新分配的）
    other_proxies_query = db.query(Proxy.remote_port).filter(
        Proxy.frps_server_id == frps_server_id,
        Proxy.remote_port.isnot(None)
    )
    if proxy_names_to_exclude:
        other_proxies_query = other_proxies_query.filter(~Proxy.name.in_(proxy_names_to_exclude))
    
    other_proxy_ports = [port[0] for port in other_proxies_query.all() if port[0] is not None]
    
    # 查询PortAllocation表中的端口
    allocated_ports = [alloc.port for alloc in port_service.get_allocated_ports(frps_server_id)]
    
    # 合并所有端口，找到最大端口号
    all_ports = set(other_proxy_ports + allocated_ports)
    max_port = max(all_ports) if all_ports else 6000
    
    # 设置合理的端口范围：从6000开始，到最大端口+1000或65535（取较小值）
    start_port = 6000
    end_port = min(max_port + 1000, 65535)
    
    # 先释放所有旧端口（但不更新代理记录，等新端口分配成功后再更新）
    for proxy in proxies_to_regenerate:
        if proxy.remote_port:
            try:
                port_service.release_port(frps_server_id, proxy.remote_port)
            except:
                pass  # 忽略释放失败
    
    # 重新分配端口的代理列表
    regenerated_proxies = []
    failed_proxies = []
    
    # 逐个分配新端口（这样可以保证连续递增）
    for proxy in proxies_to_regenerate:
        try:
            # 获取新的可用端口（排除当前分组中正在重新分配的代理的旧端口）
            new_port = port_service.get_next_available_port(
                frps_server_id, 
                start_port, 
                end_port,
                exclude_proxy_names=proxy_names_to_exclude
            )
            if new_port is None:
                failed_proxies.append({
                    "name": proxy.name,
                    "error": f"无法分配可用端口（{start_port}-{end_port} 范围内已满）"
                })
                continue
            
            # 分配新端口
            try:
                port_service.allocate_port(frps_server_id, new_port, proxy.name)
            except ValueError as e:
                failed_proxies.append({
                    "name": proxy.name,
                    "error": str(e)
                })
                continue
            
            # 更新代理的远端端口
            old_port = old_ports_map[proxy.name]
            proxy.remote_port = new_port
            regenerated_proxies.append({
                "name": proxy.name,
                "old_port": old_port,
                "new_port": new_port
            })
        
        except Exception as e:
            failed_proxies.append({
                "name": proxy.name,
                "error": str(e)
            })
    
    db.commit()
    
    return {
        "success": True,
        "message": f"已为分组 '{group_name}' 重新分配 {len(regenerated_proxies)} 个代理的远端端口",
        "group_name": group_name,
        "regenerated": len(regenerated_proxies),
        "failed": len(failed_proxies),
        "proxies": regenerated_proxies,
        "failed_proxies": failed_proxies
    }


# ── 一键安装/下载脚本 ──────────────────────────────────────────────

def _ensure_packages_dir() -> str:
    d = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), "data", "packages")
    os.makedirs(d, exist_ok=True)
    return d


def _load_versions_cache() -> dict:
    path = os.path.join(_ensure_packages_dir(), "versions_cache.json")
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _load_script_templates() -> dict:
    path = os.path.join(_ensure_packages_dir(), "install_scripts.json")
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _default_install_template(platform: str) -> str:
    if platform.startswith("windows_"):
        return load_shell_template("group_quick_install_windows.ps1")
    return load_shell_template("group_quick_install_linux.sh")


def _get_latest_package_for_platform(db: Session, platform: str):
    """查找指定平台最新版本的激活安装包（优先 versions_cache 中的 latest_version）"""
    cache = _load_versions_cache()
    latest_version = cache.get("latest_version")
    if not latest_version:
        row = db.query(FrpPackage.version).filter(
            FrpPackage.is_active == True,
            FrpPackage.platform == platform
        ).order_by(FrpPackage.id.desc()).first()
        if not row:
            return None, None
        latest_version = row.version

    pkg = db.query(FrpPackage).filter(
        FrpPackage.is_active == True,
        FrpPackage.platform == platform,
        FrpPackage.version == latest_version
    ).first()
    if not pkg:
        pkg = db.query(FrpPackage).filter(
            FrpPackage.is_active == True,
            FrpPackage.platform == platform
        ).order_by(FrpPackage.id.desc()).first()
        if pkg:
            return pkg, pkg.version
        return None, None
    return pkg, latest_version


def _get_latest_linux_amd64_package(db: Session):
    """查找最新版本 linux_amd64 平台的激活安装包"""
    return _get_latest_package_for_platform(db, "linux_amd64")


def _default_deploy_template(platform: str) -> str:
    if platform.startswith("windows_"):
        raise HTTPException(
            status_code=400,
            detail="分组一键部署脚本当前仅支持 Linux；Windows 请使用「一键安装」生成的 PowerShell 脚本。",
        )
    return load_shell_template("group_deploy_linux.sh")


def _build_deploy_script(
    db,
    pkg,
    api_key,
    install_path,
    server_name,
    group_name,
    server_base,
    upgrade: bool,
    force_config: bool,
    verify: bool = True,
    min_online: int = 1,
    verify_attempts: int = 18,
    verify_interval: int = 5,
):
    """构建统一部署脚本：可选升级二进制、可选强制覆盖配置、systemd 自启、可选部署后校验与回退"""
    download_url = f"{server_base}/api/packages/{pkg.id}/download?api_key={api_key}"
    config_url = f"{server_base}/api/frpc/config/{server_name}/{group_name}?format=toml&api_key={api_key}"
    upgrade_s = "true" if upgrade else "false"
    force_config_s = "true" if force_config else "false"
    verify_s = "true" if verify else "false"

    gn_enc = quote(group_name, safe="")
    sn_enc = quote(server_name, safe="")
    key_q = quote(api_key, safe="") if api_key else ""
    verify_url = (
        f"{server_base}/api/groups/{gn_enc}/deploy-verify"
        f"?server_name={sn_enc}&min_online={min_online}&api_key={key_q}"
    )

    template = _default_deploy_template(pkg.platform)
    return (
        template.replace("{{filename}}", pkg.filename)
        .replace("{{download_url}}", download_url)
        .replace("{{config_url}}", config_url)
        .replace("{{verify_url}}", verify_url)
        .replace("{{install_path}}", install_path)
        .replace("{{platform}}", pkg.platform)
        .replace("{{version}}", pkg.version)
        .replace("{{upgrade}}", upgrade_s)
        .replace("{{force_config}}", force_config_s)
        .replace("{{verify_enabled}}", verify_s)
        .replace("{{verify_attempts}}", str(verify_attempts))
        .replace("{{verify_interval}}", str(verify_interval))
        .replace("{{min_online}}", str(min_online))
    )


def _build_install_script(db, pkg, api_key, install_path, server_name, group_name, server_base):
    """构建安装+配置脚本"""
    download_url = f"{server_base}/api/packages/{pkg.id}/download?api_key={api_key}"
    config_url = f"{server_base}/api/frpc/config/{server_name}/{group_name}?format=toml&api_key={api_key}"
    config_line = f"\ncurl -sL \"{config_url}\" -o \"$FRP_DIR/frpc.toml\"\n"

    templates = _load_script_templates()
    template = templates.get(pkg.platform) or _default_install_template(pkg.platform)
    done_echo = ""
    if not pkg.platform.startswith("windows_"):
        done_echo = 'echo "Done. frpc installed to $FRP_DIR"\n'
    script = (
        template.replace("{{filename}}", pkg.filename)
        .replace("{{download_url}}", download_url)
        .replace("{{install_path}}", install_path)
        .replace("{{config_line}}", config_line)
        .replace("{{platform}}", pkg.platform)
        .replace("{{version}}", pkg.version)
        .replace("{{done_echo}}", done_echo)
    )
    return script


def _build_download_script(db, pkg, api_key, install_path, server_name, group_name, server_base):
    """构建下载+配置的 shell 命令"""
    download_url = f"{server_base}/api/packages/{pkg.id}/download?api_key={api_key}"
    config_url = f"{server_base}/api/frpc/config/{server_name}/{group_name}?format=toml&api_key={api_key}"
    config_line = f"\ncurl -sL \"{config_url}\" -o \"$FRP_DIR/frpc.toml\"\n"
    done_echo = 'echo "Done. frpc downloaded to $FRP_DIR"\n'
    tpl = load_shell_template("group_quick_install_linux.sh")
    return (
        tpl.replace("{{filename}}", pkg.filename)
        .replace("{{download_url}}", download_url)
        .replace("{{install_path}}", install_path)
        .replace("{{config_line}}", config_line)
        .replace("{{platform}}", pkg.platform)
        .replace("{{version}}", pkg.version)
        .replace("{{done_echo}}", done_echo)
    )


def _auth_for_script(request: Request, db: Session = Depends(get_db)):
    """脚本端点的认证：支持 API Key 或已登录用户"""
    api_key = request.query_params.get("api_key")
    if not api_key:
        api_key = request.headers.get("X-API-Key")
    if not api_key:
        authorization = request.headers.get("Authorization", "")
        if authorization.startswith("Bearer "):
            api_key = authorization[7:].strip()
    if api_key:
        obj = verify_api_key(db, api_key)
        if obj:
            return {"type": "api_key", "obj": obj, "key": api_key}
    try:
        user = get_current_user(request, db)
        return {"type": "user", "obj": user, "key": None}
    except HTTPException:
        pass
    raise HTTPException(status_code=401, detail="认证失败，请提供有效的 API Key 或登录凭证")


@router.get("/{group_name}/quick-install", response_class=PlainTextResponse)
def quick_install(
    group_name: str,
    server_name: str = Query(..., description="frps 服务器名称"),
    platform: str = Query("linux_amd64", description="目标平台"),
    install_path: str = Query("/opt/frp", description="安装路径"),
    request: Request = None,
    db: Session = Depends(get_db),
    auth_info: dict = Depends(_auth_for_script),
):
    """一键安装脚本：自动下载最新 frpc 并拉取分组配置

    用法：
      curl -sL "http://host/api/groups/mygroup/quick-install?server_name=xxx&api_key=xxx" | bash
    """
    api_key = request.query_params.get("api_key") or ""
    server_base = f"{request.url.scheme}://{request.url.netloc}"

    pkg, version = _get_latest_linux_amd64_package(db)
    if not pkg:
        raise HTTPException(status_code=404, detail="未找到可用的 linux_amd64 安装包，请先同步安装包")

    script = _build_install_script(db, pkg, api_key, install_path, server_name, group_name, server_base)
    return PlainTextResponse(content=script, media_type="text/plain; charset=utf-8")


@router.get("/{group_name}/quick-download", response_class=PlainTextResponse)
def quick_download(
    group_name: str,
    server_name: str = Query(..., description="frps 服务器名称"),
    install_path: str = Query("/opt/frp", description="安装路径"),
    request: Request = None,
    db: Session = Depends(get_db),
    auth_info: dict = Depends(_auth_for_script),
):
    """一键下载脚本：下载最新 frpc 压缩包并拉取分组配置到指定目录

    用法：
      curl -sL "http://host/api/groups/mygroup/quick-download?server_name=xxx&api_key=xxx" | bash
    """
    api_key = request.query_params.get("api_key") or ""
    server_base = f"{request.url.scheme}://{request.url.netloc}"

    pkg, version = _get_latest_linux_amd64_package(db)
    if not pkg:
        raise HTTPException(status_code=404, detail="未找到可用的 linux_amd64 安装包，请先同步安装包")

    script = _build_download_script(db, pkg, api_key, install_path, server_name, group_name, server_base)
    return PlainTextResponse(content=script, media_type="text/plain; charset=utf-8")


@router.get("/{group_name}/deploy-verify")
async def deploy_verify(
    group_name: str,
    server_name: str = Query(..., description="frps 服务器名称（与平台中名称一致）"),
    min_online: int = Query(1, ge=0, description="至少多少条代理为 online 视为通过"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """部署后校验：先向 frps 同步该服务器代理状态，再统计本分组 online 数量。

    供现场 deploy 脚本轮询；需 API Key 或登录（支持 URL ?api_key=）。
    """
    server = db.query(FrpsServer).filter(FrpsServer.name == server_name).first()
    if not server:
        raise HTTPException(status_code=404, detail=f"未找到名为「{server_name}」的 frps 服务器")

    try:
        await sync_server(db, server)
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"frps 同步失败，无法获取最新代理状态: {str(e)}",
        )

    proxies = (
        db.query(Proxy)
        .filter(
            Proxy.group_name == group_name,
            Proxy.frps_server_id == server.id,
        )
        .all()
    )
    total = len(proxies)
    online = sum(1 for p in proxies if p.status == "online")
    if total == 0:
        ok = False
    else:
        ok = online >= min_online

    return {
        "group_name": group_name,
        "server_name": server_name,
        "online": online,
        "total": total,
        "min_online": min_online,
        "ok": ok,
        "sync_ok": True,
    }


@router.get("/{group_name}/deploy", response_class=PlainTextResponse)
def group_deploy(
    group_name: str,
    server_name: str = Query(..., description="frps 服务器名称"),
    platform: str = Query("linux_amd64", description="目标平台"),
    install_path: str = Query("/opt/frp", description="安装路径"),
    upgrade: bool = Query(False, description="是否升级 frpc 二进制（已安装时）"),
    force_config: bool = Query(False, description="是否强制覆盖 frpc.toml"),
    verify: bool = Query(True, description="是否在脚本中启用部署后代理校验与失败回退"),
    min_online: int = Query(1, ge=0, description="校验时至少 online 代理数"),
    verify_attempts: int = Query(18, ge=1, le=120, description="校验最大轮询次数"),
    verify_interval: int = Query(5, ge=1, le=60, description="校验轮询间隔（秒）"),
    request: Request = None,
    db: Session = Depends(get_db),
    auth_info: dict = Depends(_auth_for_script),
):
    """统一部署脚本：首次自动安装并注册 systemd；可选升级二进制、可选覆盖配置。

    用法：
      curl -sL "http://host/api/groups/mygroup/deploy?server_name=xxx&api_key=xxx" | sudo bash
      curl -sL "...&upgrade=true&force_config=true" | sudo bash
      curl -sL "...&verify=false" | sudo bash
    """
    api_key = request.query_params.get("api_key") or auth_info.get("key") or ""
    server_base = f"{request.url.scheme}://{request.url.netloc}"

    pkg, _version = _get_latest_package_for_platform(db, platform)
    if not pkg:
        raise HTTPException(
            status_code=404,
            detail=f"未找到可用的 {platform} 安装包，请先同步或上传安装包",
        )

    script = _build_deploy_script(
        db,
        pkg,
        api_key,
        install_path,
        server_name,
        group_name,
        server_base,
        upgrade,
        force_config,
        verify=verify,
        min_online=min_online,
        verify_attempts=verify_attempts,
        verify_interval=verify_interval,
    )
    return PlainTextResponse(content=script, media_type="text/plain; charset=utf-8")


# ── 配置导入 ──────────────────────────────────────────────

def _do_import_config(db: Session, frps_server_id: int, group_name: str,
                      config_content: str, config_format: str, overwrite: bool) -> dict:
    """核心导入逻辑：解析配置内容并创建分组和代理"""

    # 自动检测格式
    if config_format == "auto":
        config_content_stripped = config_content.strip()
        if config_content_stripped.startswith("["):
            config_format = "ini"
        elif config_content_stripped.startswith("[[proxies]]") or config_content_stripped.startswith("serverAddr"):
            config_format = "toml"
        else:
            # 尝试 TOML 先（更严格），失败则 INI
            try:
                ConfigParser.parse_toml_config(config_content)
                config_format = "toml"
            except Exception:
                config_format = "ini"

    # 解析配置
    try:
        proxies = ConfigParser.parse_config(config_content, config_format)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    if not proxies:
        raise HTTPException(status_code=400, detail="配置文件中没有解析到有效的代理配置")

    # 检查服务器是否存在
    server = db.query(FrpsServer).filter(FrpsServer.id == frps_server_id).first()
    if not server:
        raise HTTPException(status_code=404, detail="服务器不存在")

    # 创建或确认分组存在
    existing_group = db.query(Group).filter(
        Group.frps_server_id == frps_server_id,
        Group.name == group_name
    ).first()
    if not existing_group:
        existing_group = Group(frps_server_id=frps_server_id, name=group_name)
        db.add(existing_group)
        db.flush()

    # 查询已有代理名称（用于判断重复）
    existing_proxy_query = db.query(Proxy).filter(
        Proxy.frps_server_id == frps_server_id,
        Proxy.group_name == group_name
    )
    existing_proxy_names = {p.name: p for p in existing_proxy_query.all()}

    port_service = PortService(db)
    created_count = 0
    updated_count = 0
    skipped_count = 0
    details = []

    for proxy_cfg in proxies:
        proxy_name = proxy_cfg["name"]
        if not proxy_name:
            skipped_count += 1
            details.append({"name": "(空)", "action": "skipped", "reason": "代理名称为空"})
            continue

        # 如果不覆盖且已存在，跳过
        if proxy_name in existing_proxy_names and not overwrite:
            skipped_count += 1
            details.append({"name": proxy_name, "action": "skipped", "reason": "代理已存在且未开启覆盖"})
            continue

        # 为代理名称自动加上分组前缀（如果原来没有的话）
        if "_" not in proxy_name or not proxy_name.startswith(group_name + "_"):
            full_proxy_name = f"{group_name}_{proxy_name}"
        else:
            full_proxy_name = proxy_name

        # 再次检查全名是否重复
        if full_proxy_name in existing_proxy_names and not overwrite:
            skipped_count += 1
            details.append({"name": full_proxy_name, "action": "skipped", "reason": "代理已存在且未开启覆盖"})
            continue

        proxy_type = proxy_cfg.get("proxy_type", "tcp")
        local_ip = proxy_cfg.get("local_ip", "127.0.0.1")
        local_port = proxy_cfg.get("local_port")
        remote_port = proxy_cfg.get("remote_port")
        custom_domains = proxy_cfg.get("custom_domains")
        subdomain = proxy_cfg.get("subdomain")

        if not local_port:
            skipped_count += 1
            details.append({"name": full_proxy_name, "action": "skipped", "reason": "缺少 local_port"})
            continue

        existing_proxy = existing_proxy_names.get(full_proxy_name)

        if existing_proxy and overwrite:
            # 覆盖更新
            existing_proxy.proxy_type = proxy_type
            existing_proxy.local_ip = local_ip
            existing_proxy.local_port = local_port
            existing_proxy.group_name = group_name

            # 如果需要 remote_port 且配置中有指定
            if remote_port and proxy_type in ("tcp", "udp"):
                if existing_proxy.remote_port != remote_port:
                    if existing_proxy.remote_port:
                        try:
                            port_service.release_port(frps_server_id, existing_proxy.remote_port)
                        except Exception:
                            pass
                    try:
                        port_service.allocate_port(frps_server_id, remote_port, full_proxy_name)
                    except ValueError:
                        pass
                    existing_proxy.remote_port = remote_port

            updated_count += 1
            details.append({"name": full_proxy_name, "action": "updated", "type": proxy_type,
                          "local_port": local_port, "remote_port": existing_proxy.remote_port})
        else:
            # 新建代理
            allocated_remote_port = remote_port

            if proxy_type in ("tcp", "udp"):
                if allocated_remote_port:
                    # 检查端口是否已被占用
                    port_taken = db.query(PortAllocation).filter(
                        PortAllocation.frps_server_id == frps_server_id,
                        PortAllocation.port == allocated_remote_port,
                        PortAllocation.is_allocated == True
                    ).first()
                    if port_taken and port_taken.allocated_to != full_proxy_name:
                        allocated_remote_port = None  # 需要重新分配
                else:
                    allocated_remote_port = None

                if not allocated_remote_port:
                    allocated_remote_port = port_service.get_next_available_port(frps_server_id, 6000, 65535)
                    if allocated_remote_port is None:
                        skipped_count += 1
                        details.append({"name": full_proxy_name, "action": "skipped", "reason": "无法分配端口"})
                        continue

                try:
                    port_service.allocate_port(frps_server_id, allocated_remote_port, full_proxy_name)
                except ValueError:
                    pass

            new_proxy = Proxy(
                frps_server_id=frps_server_id,
                name=full_proxy_name,
                group_name=group_name,
                proxy_type=proxy_type,
                local_ip=local_ip,
                local_port=local_port,
                remote_port=allocated_remote_port,
                status="offline"
            )

            db.add(new_proxy)
            existing_proxy_names[full_proxy_name] = new_proxy
            created_count += 1
            details.append({"name": full_proxy_name, "action": "created", "type": proxy_type,
                          "local_port": local_port, "remote_port": allocated_remote_port})

    db.commit()

    return {
        "success": True,
        "message": f"导入完成：创建 {created_count} 个，更新 {updated_count} 个，跳过 {skipped_count} 个代理",
        "group_name": group_name,
        "config_format": config_format,
        "total_parsed": len(proxies),
        "created": created_count,
        "updated": updated_count,
        "skipped": skipped_count,
        "overwrite": overwrite,
        "details": details
    }


@router.post("/import-config")
def import_config(
    request: ImportConfigRequest,
    db: Session = Depends(get_db),
    auth_info: dict = Depends(_auth_for_script)
):
    """从配置内容导入分组和代理

    接受 INI 或 TOML 格式的 frpc 配置内容，解析后创建分组和代理记录。
    支持 auto/ini/toml 三种格式，以及重名覆盖。
    支持通过 API Key 或登录认证调用。
    """
    return _do_import_config(
        db=db,
        frps_server_id=request.frps_server_id,
        group_name=request.group_name.strip(),
        config_content=request.config_content,
        config_format=request.config_format,
        overwrite=request.overwrite
    )


@router.post("/import-config-form")
def import_config_form(
    frps_server_id: int = Form(...),
    group_name: str = Form(...),
    config_content: str = Form(...),
    config_format: str = Form("auto"),
    overwrite: str = Form("true"),
    db: Session = Depends(get_db),
    auth_info: dict = Depends(_auth_for_script),
):
    """表单方式导入配置：供 shell 脚本 curl -F 调用，不依赖 python3。"""
    return _do_import_config(
        db=db,
        frps_server_id=frps_server_id,
        group_name=group_name.strip(),
        config_content=config_content,
        config_format=config_format,
        overwrite=overwrite.lower() in ("true", "1", "yes"),
    )



def _build_group_import_shell_script(
    frps_server_id: int,
    group_name: str,
    config_path: str,
    config_format: str,
    overwrite: bool,
    import_url: str,
    api_key: str,
) -> str:
    """生成在目标机执行的 bash 脚本：纯 curl 表单提交，不依赖 python3。"""
    tpl = load_shell_template("import_frpc_group.sh")
    return (
        tpl.replace("@@SCAN_PATH@@", shlex.quote(config_path))
        .replace("@@API_URL@@", shlex.quote(import_url))
        .replace("@@API_KEY@@", shlex.quote(api_key))
        .replace("@@GROUP_LABEL@@", shlex.quote(group_name))
        .replace("@@FRPS_ID@@", str(frps_server_id))
        .replace("@@CONFIG_FORMAT@@", shlex.quote(config_format))
        .replace("@@OVERWRITE@@", "true" if overwrite else "false")
    )


@router.get("/import-script", response_class=PlainTextResponse)
def import_script(
    frps_server_id: int = Query(..., description="frps 服务器 ID"),
    group_name: str = Query(..., description="导入的目标分组名称"),
    config_path: str = Query("/opt/frp", description="扫描路径（文件或目录）"),
    config_format: str = Query("auto", description="配置格式"),
    overwrite: bool = Query(True, description="是否覆盖已存在的同名代理，默认 true"),
    req: Request = None,
    db: Session = Depends(get_db),
    auth_info: dict = Depends(_auth_for_script),
):
    """配置导入脚本：在目标机执行，读取本地 frpc 配置并导入。

    用法：
      curl -sL "http://host/api/groups/import-script?frps_server_id=1&group_name=mygroup&config_path=/opt/frp&api_key=xxx" | bash
    """
    api_key = req.query_params.get("api_key") or ""
    server_base = f"{req.url.scheme}://{req.url.netloc}"
    import_url = f"{server_base}/api/groups/import-config-form"
    script = _build_group_import_shell_script(
        frps_server_id=frps_server_id,
        group_name=group_name,
        config_path=config_path,
        config_format=config_format,
        overwrite=overwrite,
        import_url=import_url,
        api_key=api_key,
    )
    return PlainTextResponse(content=script, media_type="text/plain; charset=utf-8")


@router.post("/{group_name}/ssh-upgrade/scan")
def ssh_upgrade_scan_group(
    group_name: str,
    body: GroupSshUpgradeRequest,
    frps_server_id: int = Query(..., description="frps 服务器 ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    cred = db.query(SshCredential).filter(SshCredential.id == body.credential_id).first()
    if not cred:
        raise HTTPException(status_code=404, detail="SSH 凭据不存在")

    job = scan_group(db, frps_server_id, group_name, cred, body.install_path)
    return ClientUpgradeJobResponse.model_validate(job)


@router.post("/{group_name}/ssh-upgrade")
def ssh_upgrade_group(
    group_name: str,
    body: GroupSshUpgradeRequest,
    frps_server_id: int = Query(..., description="frps 服务器 ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    cred = db.query(SshCredential).filter(SshCredential.id == body.credential_id).first()
    if not cred:
        raise HTTPException(status_code=404, detail="SSH 凭据不存在")

    job = upgrade_group(
        db,
        frps_server_id,
        group_name,
        cred,
        body.install_path,
        body.proxy_ids,
    )
    return ClientUpgradeJobResponse.model_validate(job)
