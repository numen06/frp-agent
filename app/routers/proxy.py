"""代理管理路由"""
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
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
    sync_from_frps: bool = Query(True, description="是否从frps实时拉取数据进行对比"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取代理列表，可选择从frps实时拉取并对比分析
    
    本程序的数据库是最全的主数据源，frps可能会丢失数据。
    当sync_from_frps=True时，会从frps拉取数据并进行对比分析。
    """
    result: Dict[str, Any] = {
        "proxies": [],
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
    
    db_proxies = query.all()
    
    # 如果需要从frps同步，进行对比分析
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
                db_proxy_map = {p.name: p for p in db_proxies}
                
                # 对比分析
                analysis = {
                    "total_in_db": len(db_proxies),
                    "total_in_frps": len(frps_proxy_list),
                    "online_proxies": [],  # frps中在线的代理
                    "missing_in_frps": [],  # 本地有但frps没有的（可能frps丢失）
                    "only_in_frps": [],  # 仅在frps中存在的（新发现的）
                    "status_changed": []  # 状态改变的
                }
                
                # 更新本地代理状态
                for db_proxy in db_proxies:
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
                
                # 检查frps中有但本地没有的代理
                for frps_name, frps_proxy in frps_proxy_map.items():
                    if frps_name not in db_proxy_map:
                        analysis["only_in_frps"].append({
                            "name": frps_name,
                            "group": Proxy.parse_group_name(frps_name),
                            "status": frps_proxy["status"],
                            "remote_port": frps_proxy.get("remote_port"),
                            "note": "仅在frps中存在，可考虑添加到本地数据库"
                        })
                
                db.commit()
                result["analysis"] = analysis
                
            except Exception as e:
                result["analysis"] = {
                    "error": f"从frps拉取数据失败: {str(e)}",
                    "note": "使用本地数据库数据"
                }
    
    # 返回代理列表（转换为响应格式）
    result["proxies"] = [
        ProxyResponse.model_validate(proxy) for proxy in db_proxies
    ]
    
    return result


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
    
    # 自动解析分组名称
    proxy_dict = proxy_data.model_dump()
    if not proxy_dict.get("group_name"):
        proxy_dict["group_name"] = Proxy.parse_group_name(proxy_data.name)
    
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
    
    # 如果更新了名称，自动更新分组
    if "name" in update_data and "group_name" not in update_data:
        update_data["group_name"] = Proxy.parse_group_name(update_data["name"])
    
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

