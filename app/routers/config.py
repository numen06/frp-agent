"""配置生成路由"""
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.database import get_db
from app.auth import get_current_user
from app.models.user import User
from app.models.frps_server import FrpsServer
from app.schemas.config import ConfigGenerateRequest, ConfigGenerateResponse
from app.services.config_service import ConfigService

router = APIRouter(prefix="/api/config", tags=["配置生成"])


@router.post("/generate", response_model=ConfigGenerateResponse)
def generate_config(
    request: ConfigGenerateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """生成 frpc 配置文件"""
    # 获取服务器配置
    server = db.query(FrpsServer).filter(FrpsServer.id == request.frps_server_id).first()
    if not server:
        raise HTTPException(status_code=404, detail="服务器不存在")
    
    config_service = ConfigService(db)
    
    # 生成配置文件
    config_content = config_service.generate_frpc_toml(
        server,
        request.proxies,
        request.user_token,
        request.use_encryption,
        request.use_compression
    )
    
    # 生成启动脚本（Linux）
    startup_script = config_service.generate_startup_script_linux()
    
    return ConfigGenerateResponse(
        config_content=config_content,
        filename="frpc.toml",
        startup_script=startup_script
    )


@router.post("/download")
def download_config(
    request: ConfigGenerateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """下载 frpc 配置文件"""
    # 获取服务器配置
    server = db.query(FrpsServer).filter(FrpsServer.id == request.frps_server_id).first()
    if not server:
        raise HTTPException(status_code=404, detail="服务器不存在")
    
    config_service = ConfigService(db)
    
    # 生成配置文件
    config_content = config_service.generate_frpc_toml(
        server,
        request.proxies,
        request.user_token,
        request.use_encryption,
        request.use_compression
    )
    
    # 返回文件下载
    return Response(
        content=config_content,
        media_type="application/toml",
        headers={
            "Content-Disposition": "attachment; filename=frpc.toml"
        }
    )


@router.get("/script/linux")
def get_linux_script(
    frpc_path: str = Query("./frpc", description="frpc 可执行文件路径"),
    config_path: str = Query("./frpc.toml", description="配置文件路径"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """下载 Linux 启动脚本"""
    config_service = ConfigService(db)
    script_content = config_service.generate_startup_script_linux(frpc_path, config_path)
    
    return Response(
        content=script_content,
        media_type="text/plain",
        headers={
            "Content-Disposition": "attachment; filename=frpc.sh"
        }
    )


@router.get("/script/windows")
def get_windows_script(
    frpc_path: str = Query("frpc.exe", description="frpc 可执行文件路径"),
    config_path: str = Query("frpc.toml", description="配置文件路径"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """下载 Windows 启动脚本"""
    config_service = ConfigService(db)
    script_content = config_service.generate_startup_script_windows(frpc_path, config_path)
    
    return Response(
        content=script_content,
        media_type="text/plain",
        headers={
            "Content-Disposition": "attachment; filename=frpc.ps1"
        }
    )


@router.get("/script/systemd")
def get_systemd_service(
    frpc_path: str = Query("/usr/local/bin/frpc", description="frpc 可执行文件路径"),
    config_path: str = Query("/etc/frp/frpc.toml", description="配置文件路径"),
    user: str = Query("nobody", description="运行用户"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """下载 systemd 服务文件"""
    config_service = ConfigService(db)
    service_content = config_service.generate_systemd_service(frpc_path, config_path, user)
    
    return Response(
        content=service_content,
        media_type="text/plain",
        headers={
            "Content-Disposition": "attachment; filename=frpc.service"
        }
    )

