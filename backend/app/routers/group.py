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
from app.models.group import Group
from app.services.port_service import PortService

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
    
    # 2. 从 Proxy 表统计代理数量
    proxy_query = db.query(
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
        
        # 自动分配远端端口
        remote_port = port_service.get_next_available_port(frps_server_id, 6000, 7000)
        if remote_port is None:
            raise HTTPException(
                status_code=500,
                detail=f"无法为代理 {config['name']} 分配可用端口（6000-7000 范围内已满）"
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
    
    # 重新分配端口的代理列表
    regenerated_proxies = []
    failed_proxies = []
    
    for proxy in proxies:
        # 只处理 TCP/UDP 类型的代理
        if proxy.proxy_type not in ["tcp", "udp"]:
            continue
        
        try:
            # 释放旧端口
            if proxy.remote_port:
                try:
                    port_service.release_port(frps_server_id, proxy.remote_port)
                except:
                    pass  # 忽略释放失败
            
            # 获取新的可用端口
            new_port = port_service.get_next_available_port(frps_server_id, 6000, 7000)
            if new_port is None:
                failed_proxies.append({
                    "name": proxy.name,
                    "error": "无法分配可用端口（6000-7000 范围内已满）"
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
            old_port = proxy.remote_port
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

