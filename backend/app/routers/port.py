"""端口管理路由"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.auth import get_current_user
from app.models.user import User
from app.schemas.port import PortAllocationResponse, PortAllocateRequest, PortReleaseRequest
from app.services.port_service import PortService

router = APIRouter(prefix="/api/ports", tags=["端口管理"])


@router.get("", response_model=List[PortAllocationResponse])
def get_ports(
    frps_server_id: int = Query(..., description="frps 服务器 ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取已分配的端口列表"""
    port_service = PortService(db)
    allocations = port_service.get_allocated_ports(frps_server_id)
    return allocations


@router.post("/allocate", response_model=PortAllocationResponse, status_code=status.HTTP_201_CREATED)
def allocate_port(
    request: PortAllocateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """手动分配端口"""
    port_service = PortService(db)
    
    try:
        allocation = port_service.allocate_port(
            request.frps_server_id,
            request.port,
            request.allocated_to
        )
        return allocation
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/release", status_code=status.HTTP_204_NO_CONTENT)
def release_port(
    request: PortReleaseRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """释放端口"""
    port_service = PortService(db)
    
    success = port_service.release_port(request.frps_server_id, request.port)
    if not success:
        raise HTTPException(status_code=404, detail="端口未被分配或不存在")
    
    return None


@router.get("/available", response_model=dict)
def get_available_port(
    frps_server_id: int = Query(..., description="frps 服务器 ID"),
    start_port: int = Query(6000, description="起始端口"),
    end_port: int = Query(7000, description="结束端口"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取下一个可用端口"""
    port_service = PortService(db)
    
    port = port_service.get_next_available_port(frps_server_id, start_port, end_port)
    if port is None:
        raise HTTPException(status_code=404, detail="没有可用端口")
    
    return {"port": port}


@router.get("/check", response_model=dict)
def check_port_available(
    frps_server_id: int = Query(..., description="frps 服务器 ID"),
    port: int = Query(..., description="端口号"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """检查端口是否可用"""
    port_service = PortService(db)
    available = port_service.is_port_available(frps_server_id, port)
    
    return {"port": port, "available": available}

