"""frpc 配置生成路由"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.database import get_db
from app.auth import get_current_user, get_auth_from_header, authenticate_user
from app.models.user import User
from app.models.frps_server import FrpsServer
from app.services.frpc_config_service import FrpcConfigService
from app.config import get_settings

router = APIRouter(prefix="/api/frpc", tags=["frpc配置生成"])
settings = get_settings()


class GenerateTokenRequest(BaseModel):
    """生成访问令牌请求"""
    username: str
    password: str


class GenerateConfigByGroupRequest(BaseModel):
    """根据分组生成配置请求"""
    group_name: str
    frps_server_id: int
    client_name: str = None
    format: str = "ini"  # 配置格式：ini 或 toml


class GenerateConfigByProxiesRequest(BaseModel):
    """根据代理列表生成配置请求"""
    proxy_ids: List[int]
    format: str = "ini"  # 配置格式：ini 或 toml


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
            client_name=request.client_name,
            format=request.format
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
        config = service.generate_config_for_proxies(
            proxy_ids=request.proxy_ids,
            format=request.format
        )
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
    format: str = Query("ini", description="配置格式：ini 或 toml"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """根据分组获取 frpc 配置文件（GET 方法）
    
    根据指定的分组名称和服务器，生成包含该分组所有代理的 frpc 配置文件。
    支持 ini 和 toml 两种格式。
    """
    try:
        service = FrpcConfigService(db)
        config = service.generate_config_for_group(
            group_name=group_name,
            frps_server_id=frps_server_id,
            client_name=client_name,
            format=format
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


@router.get("/get-my-token")
def get_my_token(
    request: Request,
    db: Session = Depends(get_db)
):
    """获取当前用户的访问令牌
    
    自动根据当前登录用户生成访问令牌，无需手动输入密码。
    Token 是 base64 编码的 username:password。
    
    返回：
    {
        "token": "生成的token",
        "username": "用户名"
    }
    """
    import base64
    
    # 从请求头中获取认证信息
    authorization = request.headers.get('Authorization')
    
    if not authorization:
        raise HTTPException(
            status_code=401,
            detail="需要认证",
            headers={"WWW-Authenticate": "Basic"},
        )
    
    # 解析认证信息
    auth_info = get_auth_from_header(authorization)
    if not auth_info:
        raise HTTPException(
            status_code=401,
            detail="认证格式错误",
            headers={"WWW-Authenticate": "Basic"},
        )
    
    username, password = auth_info
    
    # 验证用户
    user = authenticate_user(db, username, password)
    if not user:
        # 如果数据库中没有用户，使用配置中的默认认证
        if username != settings.auth_username or password != settings.auth_password:
            raise HTTPException(
                status_code=401,
                detail="用户名或密码错误",
                headers={"WWW-Authenticate": "Basic"},
            )
    
    # 生成 token
    token = base64.b64encode(f"{username}:{password}".encode()).decode()
    
    return {
        "token": token,
        "username": username
    }


@router.get("/config/direct/{server_name}/{group_name}/{filename}", response_class=PlainTextResponse)
def get_config_direct(
    server_name: str,
    group_name: str,
    filename: str,
    token: str = Query(None, description="访问令牌（可选，base64编码的username:password）"),
    client_name: str = Query(None, description="客户端名称（可选）"),
    request: Request = None,
    db: Session = Depends(get_db)
):
    """直接获取 frpc 配置文件（支持 Basic Auth 或 Token 认证）
    
    此接口支持两种认证方式：
    1. Basic Auth：在请求头中传递用户名密码
    2. Token：在URL参数中传递token（更方便）
    
    URL 格式：/api/frpc/config/direct/{server_name}/{group_name}/frpc.ini?token=xxx
    
    使用方法：
    ```bash
    # 方法1：使用 token（推荐，更简单）
    curl -f "http://your-api/api/frpc/config/direct/51jbm/dlyy/frpc.ini?token=YOUR_TOKEN" -o frpc.ini
    
    # 方法2：使用 Basic Auth
    curl -f -u username:password "http://your-api/api/frpc/config/direct/51jbm/dlyy/frpc.ini" -o frpc.ini
    ```
    """
    # 从文件名判断格式
    format = "toml" if filename.endswith(".toml") else "ini"
    
    username = None
    password = None
    use_token = False
    
    # 优先使用 token 参数认证
    if token:
        use_token = True
        try:
            import base64
            # 解码 token（base64 编码的 username:password）
            decoded = base64.b64decode(token).decode('utf-8')
            if ':' in decoded:
                username, password = decoded.split(':', 1)
            else:
                raise HTTPException(
                    status_code=401,
                    detail="Token 格式错误：无法解析用户名和密码",
                )
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=401,
                detail=f"Token 解码失败: {str(e)}",
            )
    else:
        # 使用 Basic Auth
        authorization = request.headers.get('Authorization')
        
        if not authorization:
            raise HTTPException(
                status_code=401,
                detail="需要认证（请提供 token 参数或 Basic Auth）",
                headers={"WWW-Authenticate": "Basic"},
            )
        
        # 解析认证信息
        auth_info = get_auth_from_header(authorization)
        if not auth_info:
            raise HTTPException(
                status_code=401,
                detail="认证格式错误",
                headers={"WWW-Authenticate": "Basic"},
            )
        
        username, password = auth_info
    
    # 验证用户
    user = authenticate_user(db, username, password)
    if not user:
        # 如果数据库中没有用户，使用配置中的默认认证
        if username != settings.auth_username or password != settings.auth_password:
            # 根据认证方式返回不同的错误响应
            if use_token:
                raise HTTPException(
                    status_code=401,
                    detail="Token 无效：用户名或密码错误",
                )
            else:
                raise HTTPException(
                    status_code=401,
                    detail="用户名或密码错误",
                    headers={"WWW-Authenticate": "Basic"},
                )
    
    # 查找服务器（先尝试按名称查找，如果失败再尝试按ID）
    server = db.query(FrpsServer).filter(FrpsServer.name == server_name).first()
    if not server:
        # 尝试将 server_name 作为 ID
        try:
            server_id = int(server_name)
            server = db.query(FrpsServer).filter(FrpsServer.id == server_id).first()
        except ValueError:
            pass
    
    if not server:
        raise HTTPException(status_code=404, detail=f"服务器 '{server_name}' 不存在")
    
    # 生成配置
    try:
        service = FrpcConfigService(db)
        config = service.generate_config_for_group(
            group_name=group_name,
            frps_server_id=server.id,
            client_name=client_name,
            format=format
        )
        return config
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"生成配置失败: {str(e)}")


@router.get("/install-script/direct/{server_name}/{group_name}", response_class=PlainTextResponse)
def get_install_script_direct(
    server_name: str,
    group_name: str,
    token: str = Query(None, description="访问令牌（可选）"),
    install_path: str = Query("/opt/frp", description="安装路径"),
    request: Request = None,
    db: Session = Depends(get_db)
):
    """直接获取 frpc 安装脚本（支持 Basic Auth 或 Token 认证）
    
    此接口支持两种认证方式：
    1. Basic Auth：在请求头中传递用户名密码
    2. Token：在URL参数中传递token（更方便）
    
    使用方法：
    ```bash
    # 方法1：使用 token（推荐）
    curl "http://your-api/api/frpc/install-script/direct/51jbm/dlyy?token=YOUR_TOKEN" | sudo bash
    
    # 方法2：使用 Basic Auth
    curl -u username:password "http://your-api/api/frpc/install-script/direct/51jbm/dlyy" | sudo bash
    ```
    """
    username = None
    password = None
    use_token = False
    
    # 优先使用 token 参数认证
    if token:
        use_token = True
        try:
            import base64
            # 解码 token（base64 编码的 username:password）
            decoded = base64.b64decode(token).decode('utf-8')
            if ':' in decoded:
                username, password = decoded.split(':', 1)
            else:
                raise HTTPException(
                    status_code=401,
                    detail="Token 格式错误：无法解析用户名和密码",
                )
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=401,
                detail=f"Token 解码失败: {str(e)}",
            )
    else:
        # 使用 Basic Auth
        authorization = request.headers.get('Authorization')
        
        if not authorization:
            raise HTTPException(
                status_code=401,
                detail="需要认证（请提供 token 参数或 Basic Auth）",
                headers={"WWW-Authenticate": "Basic"},
            )
        
        # 解析认证信息
        auth_info = get_auth_from_header(authorization)
        if not auth_info:
            raise HTTPException(
                status_code=401,
                detail="认证格式错误",
                headers={"WWW-Authenticate": "Basic"},
            )
        
        username, password = auth_info
    
    # 验证用户
    user = authenticate_user(db, username, password)
    if not user:
        # 如果数据库中没有用户，使用配置中的默认认证
        if username != settings.auth_username or password != settings.auth_password:
            # 根据认证方式返回不同的错误响应
            if use_token:
                raise HTTPException(
                    status_code=401,
                    detail="Token 无效：用户名或密码错误",
                )
            else:
                raise HTTPException(
                    status_code=401,
                    detail="用户名或密码错误",
                    headers={"WWW-Authenticate": "Basic"},
                )
    
    # 查找服务器（先尝试按名称查找，如果失败再尝试按ID）
    server = db.query(FrpsServer).filter(FrpsServer.name == server_name).first()
    if not server:
        # 尝试将 server_name 作为 ID
        try:
            server_id = int(server_name)
            server = db.query(FrpsServer).filter(FrpsServer.id == server_id).first()
        except ValueError:
            pass
    
    if not server:
        raise HTTPException(status_code=404, detail=f"服务器 '{server_name}' 不存在")
    
    # 生成安装脚本
    try:
        service = FrpcConfigService(db)
        # 获取请求的基础 URL
        base_url = str(request.base_url).rstrip('/')
        
        script = service.get_install_script_with_auth(
            group_name=group_name,
            frps_server_id=server.id,
            install_path=install_path,
            api_base_url=base_url,
            auth_username=username,
            auth_password=password,
            server_name=server_name
        )
        return script
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"生成安装脚本失败: {str(e)}")

