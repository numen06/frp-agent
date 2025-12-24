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
from app.models.group import Group
from app.models.proxy import Proxy
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


@router.post("/config/by-group", response_class=PlainTextResponse, deprecated=True)
def generate_config_by_group(
    request: GenerateConfigByGroupRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """根据分组生成 frpc 配置文件
    
    [已弃用] 推荐使用 GET /api/frpc/config/group/{group_name} 接口，支持 API Key 和自动创建分组。
    
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


@router.get("/config/group/{group_name}", response_class=PlainTextResponse)
def get_config_by_group_quick(
    group_name: str,
    server_id: int = Query(None, description="frps 服务器 ID（可选，不提供则使用第一个激活的服务器）"),
    client_name: str = Query(None, description="客户端名称（可选）"),
    format: str = Query("ini", description="配置格式：ini 或 toml"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """快捷获取分组配置（支持 API Key，自动创建分组）
    
    根据指定的分组名称获取 frpc 配置文件。
    如果分组不存在，会自动创建分组和默认代理配置（docker:9000, ssh:22, http:80）。
    支持 API Key 认证（URL 参数 api_key 或 Bearer Token）。
    
    参数:
    - group_name: 分组名称（路径参数）
    - server_id: 服务器 ID（可选，不提供则使用第一个激活的服务器）
    - format: 配置格式，ini 或 toml（默认 ini）
    - client_name: 客户端名称（可选）
    - api_key: API Key（URL 参数，推荐使用）
    
    使用示例:
    ```bash
    # 方式1：使用 URL 参数（推荐）
    curl "http://your-api/api/frpc/config/group/test?format=toml&api_key=YOUR_API_KEY" \
      -o frpc.toml
    
    # 方式2：使用 Bearer Token
    curl -H "Authorization: Bearer YOUR_API_KEY" \
      "http://your-api/api/frpc/config/group/test?format=toml" \
      -o frpc.toml
    ```
    """
    try:
        # 验证分组名称
        group_name = group_name.strip()
        if not group_name:
            raise HTTPException(status_code=400, detail="分组名称不能为空")
        
        if group_name == "其他":
            raise HTTPException(status_code=400, detail="不能使用'其他'作为分组名称")
        
        # 确定目标服务器
        if server_id:
            server = db.query(FrpsServer).filter(
                FrpsServer.id == server_id,
                FrpsServer.is_active == True
            ).first()
            if not server:
                raise HTTPException(status_code=404, detail=f"服务器 ID {server_id} 不存在或未激活")
        else:
            # 使用第一个激活的服务器
            server = db.query(FrpsServer).filter(FrpsServer.is_active == True).first()
            if not server:
                raise HTTPException(status_code=404, detail="没有可用的激活服务器")
            server_id = server.id
        
        # 检查分组是否存在（查询 Group 表或 Proxy 表）
        group_exists = False
        
        # 先检查 Group 表
        group_record = db.query(Group).filter(
            Group.frps_server_id == server_id,
            Group.name == group_name
        ).first()
        
        if group_record:
            group_exists = True
        else:
            # 检查 Proxy 表中是否有该分组的代理
            proxy_count = db.query(Proxy).filter(
                Proxy.frps_server_id == server_id,
                Proxy.group_name == group_name
            ).count()
            
            if proxy_count > 0:
                group_exists = True
        
        # 如果分组不存在，创建分组和默认代理
        if not group_exists:
            # 创建分组记录
            new_group = Group(
                frps_server_id=server_id,
                name=group_name
            )
            db.add(new_group)
            db.flush()  # 获取 ID 但不提交
            
            # 创建默认代理配置
            default_configs = [
                {
                    "name": f"{group_name}_docker",
                    "proxy_type": "tcp",
                    "local_ip": "127.0.0.1",
                    "local_port": 9000,
                    "remote_port": None,
                },
                {
                    "name": f"{group_name}_ssh",
                    "proxy_type": "tcp",
                    "local_ip": "127.0.0.1",
                    "local_port": 22,
                    "remote_port": None,
                },
                {
                    "name": f"{group_name}_http",
                    "proxy_type": "tcp",
                    "local_ip": "127.0.0.1",
                    "local_port": 80,
                    "remote_port": None,
                }
            ]
            
            # 检查已存在的代理名称
            existing_proxies = db.query(Proxy).filter(
                Proxy.frps_server_id == server_id,
                Proxy.group_name == group_name
            ).all()
            existing_names = set([p.name for p in existing_proxies])
            
            # 创建不存在的代理
            for config in default_configs:
                if config["name"] not in existing_names:
                    new_proxy = Proxy(
                        frps_server_id=server_id,
                        name=config["name"],
                        group_name=group_name,
                        proxy_type=config["proxy_type"],
                        local_ip=config["local_ip"],
                        local_port=config["local_port"],
                        remote_port=config["remote_port"],
                        status="offline"
                    )
                    db.add(new_proxy)
            
            db.commit()
        
        # 生成并返回配置文件
        service = FrpcConfigService(db)
        config = service.generate_config_for_group(
            group_name=group_name,
            frps_server_id=server_id,
            client_name=client_name,
            format=format
        )
        return config
        
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"生成配置失败: {str(e)}")


@router.get("/config/by-group/{group_name}", response_class=PlainTextResponse, deprecated=True)
def get_config_by_group(
    group_name: str,
    frps_server_id: int = Query(..., description="frps 服务器 ID"),
    client_name: str = Query(None, description="客户端名称（可选）"),
    format: str = Query("ini", description="配置格式：ini 或 toml"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """根据分组获取 frpc 配置文件（GET 方法）
    
    [已弃用] 推荐使用 /api/frpc/config/group/{group_name} 接口，支持 API Key 和自动创建分组。
    
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


@router.get("/convert/test-auth")
async def test_auth(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """测试认证是否成功（用于调试）"""
    return {
        "success": True,
        "message": "认证成功",
        "user_id": current_user.id,
        "username": current_user.username
    }


@router.post("/convert/ini-to-toml/direct", response_class=PlainTextResponse)
async def convert_ini_to_toml_direct(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """将INI格式的frpc配置转换为TOML格式（直接接收原始文本）
    
    仅支持 API Key 认证。
    
    使用方法（通过curl）:
    ```bash
    # 方式1：使用 API Key（URL 参数，推荐）
    curl -X POST \
      -H "Content-Type: text/plain" \
      --data-binary "@frpc.ini" \
      "http://your-api/api/frpc/convert/ini-to-toml/direct?api_key=YOUR_API_KEY" -o frpc.toml
    
    # 方式2：使用 API Key（Bearer Token）
    curl -X POST \
      -H "Content-Type: text/plain" \
      -H "Authorization: Bearer YOUR_API_KEY" \
      --data-binary "@frpc.ini" \
      http://your-api/api/frpc/convert/ini-to-toml/direct -o frpc.toml
    
    # 从管道输入
    cat frpc.ini | curl -X POST \
      -H "Content-Type: text/plain" \
      -H "Authorization: Bearer YOUR_API_KEY" \
      --data-binary @- \
      http://your-api/api/frpc/convert/ini-to-toml/direct -o frpc.toml
    ```
    """
    try:
        # 读取原始请求体
        ini_content = await request.body()
        ini_text = ini_content.decode('utf-8')
        
        # 检查是否是 HTML 响应（可能是认证失败或路由错误）
        if ini_text.strip().startswith('<!DOCTYPE') or ini_text.strip().startswith('<html'):
            raise HTTPException(
                status_code=400,
                detail="请求体内容无效：收到的是 HTML 页面而不是 INI 配置。请检查认证信息是否正确，或确认请求是否被重定向。"
            )
        
        # 检查内容是否为空
        if not ini_text.strip():
            raise HTTPException(
                status_code=400,
                detail="请求体为空，请提供有效的 INI 配置内容"
            )
        
        service = FrpcConfigService(db)
        toml_content = service.convert_ini_to_toml(ini_text)
        return toml_content
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        import traceback
        error_detail = f"转换失败: {str(e)}"
        # 记录详细错误信息用于调试
        print(f"转换错误详情: {error_detail}")
        print(f"错误堆栈: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=error_detail)


@router.post("/convert/to-toml/direct", response_class=PlainTextResponse)
async def convert_to_toml_direct_alias(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """将INI格式的frpc配置转换为TOML格式（直接接收原始文本）- 简短别名
    
    这是 /convert/ini-to-toml/direct 的简短别名，功能完全相同。
    仅支持 API Key 认证。
    """
    # 直接调用主函数
    return await convert_ini_to_toml_direct(request, db, current_user)


@router.post("/convert/to-toml/{api_key}", response_class=PlainTextResponse)
async def convert_to_toml_with_path_key(
    api_key: str,
    request: Request,
    db: Session = Depends(get_db)
):
    """将INI格式的frpc配置转换为TOML格式（支持路径参数形式的 API Key）
    
    这是为了方便使用而提供的兼容路由，API Key 可以作为路径参数。
    推荐使用查询参数形式：/convert/to-toml/direct?api_key=YOUR_API_KEY
    """
    from app.auth import verify_api_key
    from app.models.user import User
    from fastapi import HTTPException, status
    
    # 验证 API Key
    api_key_obj = verify_api_key(db, api_key)
    if not api_key_obj:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API Key 无效或已过期"
        )
    
    # 创建临时用户对象
    temp_user = User(
        id=-api_key_obj.id,
        username=f"api_key_{api_key_obj.id}",
        password_hash="",
    )
    
    # 调用主函数
    return await convert_ini_to_toml_direct(request, db, temp_user)


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
    curl -f "http://your-api/api/frpc/config/direct/test/dlyy/frpc.ini?token=YOUR_TOKEN" -o frpc.ini
    
    # 方法2：使用 Basic Auth
    curl -f -u username:password "http://your-api/api/frpc/config/direct/test/dlyy/frpc.ini" -o frpc.ini
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


@router.get("/config/{server}/{group}", response_class=PlainTextResponse)
def get_config_by_server_and_group(
    server: str,
    group: str,
    format: str = Query("ini", description="配置格式：ini 或 toml"),
    client_name: str = Query(None, description="客户端名称（可选）"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """根据服务器和分组获取 frpc 配置文件（支持 API Key 认证）
    
    根据指定的服务器名称/ID 和分组名称获取 frpc 配置文件。
    支持 API Key 认证（URL 参数 api_key 或 Bearer Token）。
    
    参数:
    - server: 服务器名称或 ID（路径参数）
    - group: 分组名称（路径参数）
    - format: 配置格式，ini 或 toml（默认 ini）
    - client_name: 客户端名称（可选）
    - api_key: API Key（URL 参数，推荐使用）
    
    使用示例:
    ```bash
    # 方式1：使用 URL 参数 api_key（推荐）
    curl "http://your-api/api/frpc/config/test_server/my_group?format=toml&api_key=YOUR_API_KEY" \
      -o frpc.toml
    
    # 方式2：使用 Bearer Token
    curl -H "Authorization: Bearer YOUR_API_KEY" \
      "http://your-api/api/frpc/config/test_server/my_group?format=toml" \
      -o frpc.toml
    
    # 方式3：使用 Basic Auth
    curl -u username:password \
      "http://your-api/api/frpc/config/test_server/my_group?format=toml" \
      -o frpc.toml
    ```
    """
    try:
        # 验证分组名称
        group = group.strip()
        if not group:
            raise HTTPException(status_code=400, detail="分组名称不能为空")
        
        if group == "其他":
            raise HTTPException(status_code=400, detail="不能使用'其他'作为分组名称")
        
        # 查找服务器（先尝试按名称查找，如果失败再尝试按ID）
        server_obj = db.query(FrpsServer).filter(FrpsServer.name == server).first()
        if not server_obj:
            # 尝试将 server 作为 ID
            try:
                server_id = int(server)
                server_obj = db.query(FrpsServer).filter(
                    FrpsServer.id == server_id,
                    FrpsServer.is_active == True
                ).first()
            except ValueError:
                pass
        
        if not server_obj:
            raise HTTPException(status_code=404, detail=f"服务器 '{server}' 不存在")
        
        if not server_obj.is_active:
            raise HTTPException(status_code=404, detail=f"服务器 '{server}' 未激活")
        
        server_id = server_obj.id
        
        # 检查分组是否存在（查询 Group 表或 Proxy 表）
        group_exists = False
        
        # 先检查 Group 表
        group_record = db.query(Group).filter(
            Group.frps_server_id == server_id,
            Group.name == group
        ).first()
        
        if group_record:
            group_exists = True
        else:
            # 检查 Proxy 表中是否有该分组的代理
            proxy_count = db.query(Proxy).filter(
                Proxy.frps_server_id == server_id,
                Proxy.group_name == group
            ).count()
            
            if proxy_count > 0:
                group_exists = True
        
        if not group_exists:
            raise HTTPException(
                status_code=404, 
                detail=f"分组 '{group}' 在服务器 '{server}' 中不存在"
            )
        
        # 生成并返回配置文件
        service = FrpcConfigService(db)
        config = service.generate_config_for_group(
            group_name=group,
            frps_server_id=server_id,
            client_name=client_name,
            format=format
        )
        return config
        
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"生成配置失败: {str(e)}")



