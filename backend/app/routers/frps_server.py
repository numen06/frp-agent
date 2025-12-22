"""frps 服务器管理路由"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.auth import get_current_user
from app.models.user import User
from app.models.frps_server import FrpsServer
from app.schemas.frps_server import FrpsServerCreate, FrpsServerUpdate, FrpsServerResponse
from app.scheduler import sync_server

router = APIRouter(prefix="/api/servers", tags=["frps服务器管理"])


@router.get("", response_model=List[FrpsServerResponse])
def get_servers(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取所有 frps 服务器列表"""
    servers = db.query(FrpsServer).all()
    return servers


@router.get("/{server_id}", response_model=FrpsServerResponse)
def get_server(
    server_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取指定 frps 服务器详情"""
    server = db.query(FrpsServer).filter(FrpsServer.id == server_id).first()
    if not server:
        raise HTTPException(status_code=404, detail="服务器不存在")
    return server


@router.post("", response_model=FrpsServerResponse, status_code=status.HTTP_201_CREATED)
def create_server(
    server_data: FrpsServerCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """创建新的 frps 服务器配置"""
    # 检查名称是否已存在
    existing = db.query(FrpsServer).filter(FrpsServer.name == server_data.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="服务器名称已存在")
    
    server = FrpsServer(**server_data.model_dump())
    db.add(server)
    db.commit()
    db.refresh(server)
    return server


@router.put("/{server_id}", response_model=FrpsServerResponse)
def update_server(
    server_id: int,
    server_data: FrpsServerUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """更新 frps 服务器配置"""
    server = db.query(FrpsServer).filter(FrpsServer.id == server_id).first()
    if not server:
        raise HTTPException(status_code=404, detail="服务器不存在")
    
    # 更新字段
    update_data = server_data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(server, key, value)
    
    db.commit()
    db.refresh(server)
    return server


@router.delete("/{server_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_server(
    server_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """删除 frps 服务器配置"""
    server = db.query(FrpsServer).filter(FrpsServer.id == server_id).first()
    if not server:
        raise HTTPException(status_code=404, detail="服务器不存在")
    
    db.delete(server)
    db.commit()
    return None


@router.post("/{server_id}/test")
async def test_server(
    server_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """测试 frps 服务器连接"""
    import httpx
    from datetime import datetime
    
    server = db.query(FrpsServer).filter(FrpsServer.id == server_id).first()
    if not server:
        raise HTTPException(status_code=404, detail="服务器不存在")
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # 尝试获取服务器状态
            response = await client.get(
                f"{server.api_base_url.rstrip('/')}/proxy/tcp",
                auth=(server.auth_username, server.auth_password)
            )
            response.raise_for_status()
            
            # 更新测试状态
            server.last_test_status = "online"
            server.last_test_time = datetime.utcnow()
            server.last_test_message = "连接成功"
            db.commit()
            
            # 测试成功后自动同步代理列表到数据库
            try:
                await sync_server(db, server)
            except Exception as sync_error:
                # 同步失败不影响测试结果，但记录错误信息
                server.last_test_message = f"连接成功，但同步代理列表失败: {str(sync_error)}"
                db.commit()
            
            return {
                "success": True,
                "message": "连接成功",
                "status_code": response.status_code
            }
    except httpx.TimeoutException:
        # 更新测试状态
        server.last_test_status = "offline"
        server.last_test_time = datetime.utcnow()
        server.last_test_message = "连接超时，请检查服务器地址和端口"
        db.commit()
        
        return {
            "success": False,
            "message": "连接超时，请检查服务器地址和端口"
        }
    except httpx.HTTPStatusError as e:
        # 更新测试状态
        server.last_test_status = "offline"
        server.last_test_time = datetime.utcnow()
        if e.response.status_code == 401:
            server.last_test_message = "认证失败，请检查用户名和密码"
            db.commit()
            return {
                "success": False,
                "message": "认证失败，请检查用户名和密码"
            }
        server.last_test_message = f"服务器返回错误: {e.response.status_code}"
        db.commit()
        return {
            "success": False,
            "message": f"服务器返回错误: {e.response.status_code}"
        }
    except Exception as e:
        # 更新测试状态
        server.last_test_status = "offline"
        server.last_test_time = datetime.utcnow()
        server.last_test_message = f"连接失败: {str(e)}"
        db.commit()
        
        return {
            "success": False,
            "message": f"连接失败: {str(e)}"
        }

