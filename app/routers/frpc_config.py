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
from app.models.temp_config import TempConfig
from app.services.frpc_config_service import FrpcConfigService
from app.config import get_settings
from datetime import datetime

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


@router.post("/config/by-proxies")
def generate_config_by_proxies(
    request: GenerateConfigByProxiesRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """根据代理ID列表生成 frpc 配置文件（临时配置，24小时有效）
    
    根据指定的代理ID列表生成临时配置文件。
    此配置会保存24小时，之后自动删除。
    
    返回：
    {
        "config": "配置内容",
        "temp_id": "临时配置ID",
        "temp_group": "临时分组名",
        "expires_at": "过期时间"
    }
    """
    try:
        import secrets
        from app.models.proxy import Proxy
        
        service = FrpcConfigService(db)
        config = service.generate_config_for_proxies(
            proxy_ids=request.proxy_ids,
            format=request.format
        )
        
        # 获取代理信息以确定服务器
        proxies = db.query(Proxy).filter(Proxy.id.in_(request.proxy_ids)).first()
        if not proxies:
            raise ValueError("未找到代理")
        
        # 获取服务器信息
        server = db.query(FrpsServer).filter(FrpsServer.id == proxies.frps_server_id).first()
        if not server:
            raise ValueError("服务器不存在")
        
        # 生成临时分组名（带随机ID）
        random_id = secrets.token_urlsafe(8)
        temp_group = f"temp_sel_{random_id}"
        
        # 创建临时配置
        temp_config = TempConfig.create_temp_config(
            server_name=server.name,
            group_name=temp_group,
            config_content=config,
            format=request.format,
            hours=24
        )
        
        db.add(temp_config)
        db.commit()
        db.refresh(temp_config)
        
        return {
            "config": config,
            "temp_id": temp_config.config_id,
            "temp_group": temp_group,
            "server_name": server.name,
            "format": request.format,
            "expires_at": temp_config.expires_at.isoformat(),
            "note": "此为临时配置，24小时后自动删除。推荐使用分组配置作为长期使用。"
        }
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


@router.get("/config/temp/{config_id}", response_class=PlainTextResponse)
def get_temp_config(
    config_id: str,
    db: Session = Depends(get_db)
):
    """获取临时配置（无需认证，24小时有效）
    
    用于访问选择代理生成的临时配置。
    临时配置24小时后自动失效。
    """
    # 查找临时配置
    temp_config = db.query(TempConfig).filter(TempConfig.config_id == config_id).first()
    
    if not temp_config:
        raise HTTPException(status_code=404, detail="临时配置不存在或已过期")
    
    # 检查是否过期
    if temp_config.is_expired:
        # 删除过期配置
        db.delete(temp_config)
        db.commit()
        raise HTTPException(status_code=410, detail="临时配置已过期（24小时有效期）")
    
    return temp_config.config_content


class ConvertIniToTomlRequest(BaseModel):
    """INI转TOML请求"""
    ini_content: str


@router.post("/convert/ini-to-toml", response_class=PlainTextResponse)
def convert_ini_to_toml(
    request: ConvertIniToTomlRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """将INI格式的frpc配置转换为TOML格式
    
    使用方法（通过curl）:
    ```bash
    curl -u username:password -X POST \
      -H "Content-Type: application/json" \
      -d '{"ini_content":"$(cat frpc.ini)"}' \
      http://your-api/api/frpc/convert/ini-to-toml
    ```
    
    或者更简单的方式：
    ```bash
    curl -u username:password -X POST \
      -H "Content-Type: application/json" \
      --data-binary "@frpc.ini" \
      http://your-api/api/frpc/convert/ini-to-toml/direct
    ```
    """
    try:
        service = FrpcConfigService(db)
        toml_content = service.convert_ini_to_toml(request.ini_content)
        return toml_content
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"转换失败: {str(e)}")


@router.post("/convert/ini-to-toml/direct", response_class=PlainTextResponse)
async def convert_ini_to_toml_direct(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """将INI格式的frpc配置转换为TOML格式（直接接收原始文本）
    
    使用方法（通过curl）:
    ```bash
    # 从文件转换
    curl -u username:password -X POST \
      -H "Content-Type: text/plain" \
      --data-binary "@frpc.ini" \
      http://your-api/api/frpc/convert/ini-to-toml/direct -o frpc.toml
    
    # 或者从管道输入
    cat frpc.ini | curl -u username:password -X POST \
      -H "Content-Type: text/plain" \
      --data-binary @- \
      http://your-api/api/frpc/convert/ini-to-toml/direct
    ```
    """
    try:
        # 读取原始请求体
        ini_content = await request.body()
        ini_text = ini_content.decode('utf-8')
        
        service = FrpcConfigService(db)
        toml_content = service.convert_ini_to_toml(ini_text)
        return toml_content
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"转换失败: {str(e)}")


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



