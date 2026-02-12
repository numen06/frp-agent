"""代理管理路由"""
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime

from app.database import get_db
from app.auth import get_current_user
from app.models.user import User
from app.models.proxy import Proxy
from app.models.frps_server import FrpsServer
from app.schemas.proxy import ProxyCreate, ProxyUpdate, ProxyResponse
from app.services.port_service import PortService
from app.frps_client import FrpsClient

router = APIRouter(prefix="/api/proxies", tags=["代理管理"])


@router.get("")
async def get_proxies(
    frps_server_id: Optional[int] = Query(None, description="按服务器ID过滤"),
    group_name: Optional[str] = Query(None, description="按分组过滤"),
    status_filter: Optional[str] = Query(None, description="按状态过滤"),
    search: Optional[str] = Query(None, description="搜索代理名称或分组"),
    page: int = Query(1, ge=1, description="页码，从1开始"),
    page_size: int = Query(10, ge=1, le=1000, description="每页数量"),
    sync_from_frps: bool = Query(False, description="是否从frps实时拉取数据进行对比"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取代理列表，支持分页和搜索，可选择从frps实时拉取并对比分析
    
    本程序的数据库是最全的主数据源，frps可能会丢失数据。
    当sync_from_frps=True时，会从frps拉取数据并进行对比分析。
    """
    result: Dict[str, Any] = {
        "items": [],
        "page": page,
        "page_size": page_size,
        "total": 0,
        "analysis": None
    }
    
    # 从数据库获取代理列表（主数据源）
    query = db.query(Proxy)
    
    if frps_server_id:
        query = query.filter(Proxy.frps_server_id == frps_server_id)
    
    if group_name:
        query = query.filter(Proxy.group_name == group_name)
    
    if status_filter:
        query = query.filter(Proxy.status == status_filter)
    
    # 搜索功能：搜索代理名称或分组
    if search:
        search_pattern = f"%{search}%"
        query = query.filter(
            (Proxy.name.like(search_pattern)) | 
            (Proxy.group_name.like(search_pattern))
        )
    
    # 如果需要从frps同步，先进行同步（在分页之前）
    if sync_from_frps and frps_server_id:
        server = db.query(FrpsServer).filter(FrpsServer.id == frps_server_id).first()
        if server:
            try:
                # 从frps拉取数据
                client = FrpsClient(server)
                all_frps_proxies = await client.get_all_proxies()
                
                # 合并所有类型的代理
                frps_proxy_list = []
                for proxy_type, proxies in all_frps_proxies.items():
                    for proxy_data in proxies:
                        parsed = client.parse_proxy_info(proxy_data)
                        parsed["proxy_type"] = proxy_type
                        frps_proxy_list.append(parsed)
                
                # 创建frps代理名称映射
                frps_proxy_map = {p["name"]: p for p in frps_proxy_list}
                
                # 获取所有匹配的代理（不仅仅是当前页）
                all_matching_proxies = query.all()
                db_proxy_map = {p.name: p for p in all_matching_proxies}
                
                # 对比分析
                analysis = {
                    "total_in_db": len(all_matching_proxies),
                    "total_in_frps": len(frps_proxy_list),
                    "online_proxies": [],  # frps中在线的代理
                    "missing_in_frps": [],  # 本地有但frps没有的（可能frps丢失）
                    "only_in_frps": [],  # 仅在frps中存在的（新发现的）
                    "status_changed": []  # 状态改变的
                }
                
                # 更新本地代理状态（更新所有匹配的代理，不仅仅是当前页）
                for db_proxy in all_matching_proxies:
                    frps_proxy = frps_proxy_map.get(db_proxy.name)
                    
                    if frps_proxy:
                        # frps中存在，更新状态
                        old_status = db_proxy.status
                        new_status = frps_proxy["status"]
                        
                        if old_status != new_status:
                            db_proxy.status = new_status
                            db_proxy.updated_at = datetime.utcnow()
                            analysis["status_changed"].append({
                                "name": db_proxy.name,
                                "group": db_proxy.group_name,
                                "old_status": old_status,
                                "new_status": new_status
                            })
                        
                        if new_status == "online":
                            analysis["online_proxies"].append({
                                "name": db_proxy.name,
                                "group": db_proxy.group_name,
                                "remote_port": frps_proxy.get("remote_port")
                            })
                    else:
                        # frps中不存在，可能是frps丢失的数据
                        if db_proxy.status == "online":
                            db_proxy.status = "offline"
                            db_proxy.updated_at = datetime.utcnow()
                        
                        analysis["missing_in_frps"].append({
                            "name": db_proxy.name,
                            "group": db_proxy.group_name,
                            "last_status": db_proxy.status,
                            "note": "本地有记录但frps中不存在，可能frps数据丢失"
                        })
                
                # 检查frps中有但本地没有的代理，自动添加到数据库
                for frps_name, frps_proxy in frps_proxy_map.items():
                    if frps_name not in db_proxy_map:
                        # 自动创建新代理到数据库
                        group_name = Proxy.parse_group_name(frps_name)
                        new_proxy = Proxy(
                            frps_server_id=server.id,
                            name=frps_name,
                            proxy_type=frps_proxy["proxy_type"],
                            remote_port=frps_proxy.get("remote_port"),
                            local_ip=frps_proxy.get("local_ip", "127.0.0.1"),
                            local_port=0,  # 需要后续识别
                            status=frps_proxy["status"],
                            group_name=group_name
                        )
                        db.add(new_proxy)
                        
                        analysis["only_in_frps"].append({
                            "name": frps_name,
                            "group": group_name,
                            "status": frps_proxy["status"],
                            "remote_port": frps_proxy.get("remote_port"),
                            "note": "已自动添加到本地数据库"
                        })
                
                db.commit()
                result["analysis"] = analysis
                
                # 同步后，重新构建查询（因为可能添加了新代理）
                query = db.query(Proxy)
                
                if frps_server_id:
                    query = query.filter(Proxy.frps_server_id == frps_server_id)
                
                if group_name:
                    query = query.filter(Proxy.group_name == group_name)
                
                if status_filter:
                    query = query.filter(Proxy.status == status_filter)
                
                if search:
                    search_pattern = f"%{search}%"
                    query = query.filter(
                        (Proxy.name.like(search_pattern)) | 
                        (Proxy.group_name.like(search_pattern))
                    )
                
            except Exception as e:
                result["analysis"] = {
                    "error": f"从frps拉取数据失败: {str(e)}",
                    "note": "使用本地数据库数据"
                }

    # 按 (frps_server_id, name) 去重：同一服务器下代理名称唯一，只保留每组中 id 最大的记录
    keep_ids_subq = db.query(func.max(Proxy.id).label('keep_id')).group_by(
        Proxy.frps_server_id, Proxy.name
    )
    if frps_server_id:
        keep_ids_subq = keep_ids_subq.filter(Proxy.frps_server_id == frps_server_id)
    if group_name:
        keep_ids_subq = keep_ids_subq.filter(Proxy.group_name == group_name)
    if status_filter:
        keep_ids_subq = keep_ids_subq.filter(Proxy.status == status_filter)
    if search:
        keep_ids_subq = keep_ids_subq.filter(
            (Proxy.name.like(search_pattern)) | (Proxy.group_name.like(search_pattern))
        )
    keep_ids_subq = keep_ids_subq.subquery()
    query = query.filter(Proxy.id.in_(db.query(keep_ids_subq.c.keep_id)))

    # 计算总数
    total = query.count()

    # 应用分页
    offset = (page - 1) * page_size
    db_proxies = query.order_by(Proxy.created_at.desc()).offset(offset).limit(page_size).all()

    # 返回代理列表（转换为响应格式）
    result["items"] = [
        ProxyResponse.model_validate(proxy) for proxy in db_proxies
    ]
    result["total"] = total
    
    return result


@router.post("/clean-duplicates", status_code=status.HTTP_200_OK)
def clean_duplicate_proxies(
    frps_server_id: Optional[int] = Query(None, description="只清理指定服务器，不传则清理全部"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """清理重复代理：同一服务器下同一名称的代理只保留 id 最大的一条"""
    base_query = db.query(Proxy)
    if frps_server_id:
        base_query = base_query.filter(Proxy.frps_server_id == frps_server_id)

    # 找出每组 (frps_server_id, name) 要保留的 id
    keep_ids_subq = db.query(func.max(Proxy.id).label('keep_id')).group_by(
        Proxy.frps_server_id, Proxy.name
    )
    if frps_server_id:
        keep_ids_subq = keep_ids_subq.filter(Proxy.frps_server_id == frps_server_id)
    keep_ids = {row[0] for row in keep_ids_subq.all()}
    if not keep_ids:
        return {"message": "没有需要清理的重复记录", "deleted_count": 0}

    # 删除不在保留列表中的代理
    to_delete = base_query.filter(~Proxy.id.in_(keep_ids)).all()
    deleted_count = len(to_delete)
    for proxy in to_delete:
        if proxy.remote_port:
            try:
                port_service = PortService(db)
                port_service.release_port(proxy.frps_server_id, proxy.remote_port)
            except Exception:
                pass
        db.delete(proxy)
    db.commit()
    return {
        "message": f"已清理 {deleted_count} 条重复代理记录",
        "deleted_count": deleted_count
    }


@router.get("/{proxy_id}", response_model=ProxyResponse)
def get_proxy(
    proxy_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取代理详情"""
    proxy = db.query(Proxy).filter(Proxy.id == proxy_id).first()
    if not proxy:
        raise HTTPException(status_code=404, detail="代理不存在")
    return proxy


@router.post("", response_model=ProxyResponse, status_code=status.HTTP_201_CREATED)
def create_proxy(
    proxy_data: ProxyCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """创建新代理"""
    # 检查名称是否已存在
    existing = db.query(Proxy).filter(
        Proxy.frps_server_id == proxy_data.frps_server_id,
        Proxy.name == proxy_data.name
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="代理名称已存在")
    
    # 自动解析分组名称
    proxy_dict = proxy_data.model_dump()
    if not proxy_dict.get("group_name"):
        proxy_dict["group_name"] = Proxy.parse_group_name(proxy_data.name)
    
    # 自动识别本地端口（如果端口为 0 或未设置）
    if not proxy_dict.get("local_port") or proxy_dict.get("local_port") == 0:
        detected_port = Proxy.auto_detect_local_port(proxy_data.name)
        if detected_port > 0:
            proxy_dict["local_port"] = detected_port
        else:
            # 如果无法自动识别，仍然需要一个有效的端口
            raise HTTPException(
                status_code=400, 
                detail="无法从代理名称自动识别本地端口，请手动指定 local_port"
            )
    
    # 如果是 TCP/UDP 代理且指定了端口，检查端口是否可用
    if proxy_data.proxy_type in ["tcp", "udp"] and proxy_data.remote_port:
        port_service = PortService(db)
        if not port_service.is_port_available(proxy_data.frps_server_id, proxy_data.remote_port):
            raise HTTPException(status_code=400, detail=f"端口 {proxy_data.remote_port} 已被占用")
        
        # 分配端口
        try:
            port_service.allocate_port(
                proxy_data.frps_server_id,
                proxy_data.remote_port,
                proxy_data.name
            )
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
    
    proxy = Proxy(**proxy_dict)
    db.add(proxy)
    db.commit()
    db.refresh(proxy)
    return proxy


@router.put("/{proxy_id}", response_model=ProxyResponse)
def update_proxy(
    proxy_id: int,
    proxy_data: ProxyUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """更新代理配置"""
    proxy = db.query(Proxy).filter(Proxy.id == proxy_id).first()
    if not proxy:
        raise HTTPException(status_code=404, detail="代理不存在")
    
    # 更新字段
    update_data = proxy_data.model_dump(exclude_unset=True)
    
    # 如果更新了名称，自动更新分组和本地端口
    if "name" in update_data:
        # 自动更新分组
        if "group_name" not in update_data:
            update_data["group_name"] = Proxy.parse_group_name(update_data["name"])
        
        # 如果本地端口为 0，尝试自动识别
        current_local_port = update_data.get("local_port", proxy.local_port)
        if current_local_port == 0:
            detected_port = Proxy.auto_detect_local_port(update_data["name"])
            if detected_port > 0:
                update_data["local_port"] = detected_port
    
    # 如果直接更新本地端口为 0，尝试自动识别
    if "local_port" in update_data and update_data["local_port"] == 0:
        proxy_name = update_data.get("name", proxy.name)
        detected_port = Proxy.auto_detect_local_port(proxy_name)
        if detected_port > 0:
            update_data["local_port"] = detected_port
        else:
            raise HTTPException(
                status_code=400, 
                detail="无法从代理名称自动识别本地端口，请手动指定 local_port"
            )
    
    # 如果更新了远程端口，需要检查端口可用性
    if "remote_port" in update_data and update_data["remote_port"] != proxy.remote_port:
        port_service = PortService(db)
        new_port = update_data["remote_port"]
        
        if not port_service.is_port_available(proxy.frps_server_id, new_port):
            raise HTTPException(status_code=400, detail=f"端口 {new_port} 已被占用")
        
        # 释放旧端口，分配新端口
        if proxy.remote_port:
            port_service.release_port(proxy.frps_server_id, proxy.remote_port)
        
        port_service.allocate_port(proxy.frps_server_id, new_port, proxy.name)
    
    for key, value in update_data.items():
        setattr(proxy, key, value)
    
    db.commit()
    db.refresh(proxy)
    return proxy


@router.delete("/{proxy_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_proxy(
    proxy_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """删除代理"""
    proxy = db.query(Proxy).filter(Proxy.id == proxy_id).first()
    if not proxy:
        raise HTTPException(status_code=404, detail="代理不存在")
    
    # 释放端口
    if proxy.remote_port:
        port_service = PortService(db)
        port_service.release_port(proxy.frps_server_id, proxy.remote_port)
    
    db.delete(proxy)
    db.commit()
    return None


@router.post("/batch-detect-ports", status_code=status.HTTP_200_OK)
def batch_detect_ports(
    frps_server_id: int = Query(..., description="服务器ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """批量识别端口为0的代理的本地端口
    
    扫描指定服务器的所有代理，对于本地端口为0的代理，
    根据代理名称自动识别并更新端口号
    """
    # 查询所有本地端口为0的代理
    proxies_with_zero_port = db.query(Proxy).filter(
        Proxy.frps_server_id == frps_server_id,
        Proxy.local_port == 0
    ).all()
    
    if not proxies_with_zero_port:
        return {
            "message": "没有需要识别的代理（本地端口都不为0）",
            "total": 0,
            "detected": 0,
            "failed": 0,
            "results": []
        }
    
    results = []
    detected_count = 0
    failed_count = 0
    
    for proxy in proxies_with_zero_port:
        detected_port = Proxy.auto_detect_local_port(proxy.name)
        
        if detected_port > 0:
            # 成功识别
            old_port = proxy.local_port
            proxy.local_port = detected_port
            proxy.updated_at = datetime.utcnow()
            detected_count += 1
            results.append({
                "id": proxy.id,
                "name": proxy.name,
                "group": proxy.group_name,
                "old_port": old_port,
                "new_port": detected_port,
                "status": "success"
            })
        else:
            # 无法识别
            failed_count += 1
            results.append({
                "id": proxy.id,
                "name": proxy.name,
                "group": proxy.group_name,
                "old_port": 0,
                "new_port": 0,
                "status": "failed",
                "message": "无法从代理名称识别端口"
            })
    
    db.commit()
    
    return {
        "message": f"批量识别完成：成功 {detected_count} 个，失败 {failed_count} 个",
        "total": len(proxies_with_zero_port),
        "detected": detected_count,
        "failed": failed_count,
        "results": results
    }

