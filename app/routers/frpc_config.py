"""frpc 配置生成路由"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.database import get_db
from app.auth import get_current_user
from app.models.user import User
from app.services.frpc_config_service import FrpcConfigService

router = APIRouter(prefix="/api/frpc", tags=["frpc配置生成"])


class GenerateConfigByGroupRequest(BaseModel):
    """根据分组生成配置请求"""
    group_name: str
    frps_server_id: int
    client_name: str = None


class GenerateConfigByProxiesRequest(BaseModel):
    """根据代理列表生成配置请求"""
    proxy_ids: List[int]


@router.post("/config/by-group", response_class=PlainTextResponse)
def generate_config_by_group(
    request: GenerateConfigByGroupRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """根据分组生成 frpc 配置文件
    
    根据指定的分组名称和服务器，生成包含该分组所有代理的 frpc 配置文件。
    """
    try:
        service = FrpcConfigService(db)
        config = service.generate_config_for_group(
            group_name=request.group_name,
            frps_server_id=request.frps_server_id,
            client_name=request.client_name
        )
        return config
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"生成配置失败: {str(e)}")


@router.post("/config/by-proxies", response_class=PlainTextResponse)
def generate_config_by_proxies(
    request: GenerateConfigByProxiesRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """根据代理ID列表生成 frpc 配置文件
    
    根据指定的代理ID列表生成 frpc 配置文件。
    """
    try:
        service = FrpcConfigService(db)
        config = service.generate_config_for_proxies(proxy_ids=request.proxy_ids)
        return config
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"生成配置失败: {str(e)}")


@router.get("/config/by-group/{group_name}", response_class=PlainTextResponse)
def get_config_by_group(
    group_name: str,
    frps_server_id: int = Query(..., description="frps 服务器 ID"),
    client_name: str = Query(None, description="客户端名称（可选）"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """根据分组获取 frpc 配置文件（GET 方法）
    
    根据指定的分组名称和服务器，生成包含该分组所有代理的 frpc 配置文件。
    """
    try:
        service = FrpcConfigService(db)
        config = service.generate_config_for_group(
            group_name=group_name,
            frps_server_id=frps_server_id,
            client_name=client_name
        )
        return config
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"生成配置失败: {str(e)}")


@router.post("/install-script/by-group", response_class=PlainTextResponse)
def generate_install_script_by_group(
    request: GenerateConfigByGroupRequest,
    install_path: str = Query("/etc/frp", description="安装路径"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """根据分组生成 frpc 安装脚本
    
    生成一键安装脚本，包含：
    1. 下载 frpc
    2. 生成配置文件
    3. 创建 systemd 服务
    4. 启动服务
    """
    try:
        service = FrpcConfigService(db)
        script = service.get_install_script(
            group_name=request.group_name,
            frps_server_id=request.frps_server_id,
            install_path=install_path
        )
        return script
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"生成安装脚本失败: {str(e)}")


@router.get("/install-script/by-group/{group_name}", response_class=PlainTextResponse)
def get_install_script_by_group(
    group_name: str,
    frps_server_id: int = Query(..., description="frps 服务器 ID"),
    install_path: str = Query("/etc/frp", description="安装路径"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """根据分组获取 frpc 安装脚本（GET 方法）
    
    生成一键安装脚本，包含：
    1. 下载 frpc
    2. 生成配置文件
    3. 创建 systemd 服务
    4. 启动服务
    
    使用方法：
    ```bash
    curl -o install.sh "http://your-api/api/frpc/install-script/by-group/dlyy?frps_server_id=1"
    chmod +x install.sh
    sudo ./install.sh
    ```
    """
    try:
        service = FrpcConfigService(db)
        script = service.get_install_script(
            group_name=group_name,
            frps_server_id=frps_server_id,
            install_path=install_path
        )
        return script
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"生成安装脚本失败: {str(e)}")

