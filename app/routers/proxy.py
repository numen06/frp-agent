"""代理管理路由"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.auth import get_current_user
from app.models.user import User
from app.models.proxy import Proxy
from app.schemas.proxy import ProxyCreate, ProxyUpdate, ProxyResponse
from app.services.port_service import PortService

router = APIRouter(prefix="/api/proxies", tags=["代理管理"])


@router.get("", response_model=List[ProxyResponse])
def get_proxies(
    frps_server_id: Optional[int] = Query(None, description="按服务器ID过滤"),
    status_filter: Optional[str] = Query(None, description="按状态过滤"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取代理列表"""
    query = db.query(Proxy)
    
    if frps_server_id:
        query = query.filter(Proxy.frps_server_id == frps_server_id)
    
    if status_filter:
        query = query.filter(Proxy.status == status_filter)
    
    proxies = query.all()
    return proxies


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
    
    proxy = Proxy(**proxy_data.model_dump())
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

