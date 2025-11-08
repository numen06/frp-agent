"""配置文件导入路由"""
from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Body, Request
from sqlalchemy.orm import Session
from datetime import datetime
import os
from pydantic import BaseModel

from app.database import get_db
from app.auth import get_current_user
from app.models.user import User
from app.models.proxy import Proxy
from app.models.frps_server import FrpsServer
from app.services.config_parser import ConfigParser
from app.services.port_service import PortService

router = APIRouter(prefix="/api/config", tags=["配置导入"])


class ConfigImportRequest(BaseModel):
    """配置导入请求"""
    content: str
    format: str  # 'ini' 或 'toml'
    frps_server_id: int
    group_name: Optional[str] = None


@router.post("/import")
async def import_config(
    file: UploadFile = File(..., description="frpc 配置文件（.ini 或 .toml）"),
    frps_server_id: int = Form(..., description="frps 服务器 ID"),
    group_name: str = Form(None, description="分组名称（可选，优先使用此分组）"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """导入 frpc 配置文件
    
    支持 INI 和 TOML 格式的配置文件。
    对于已存在的代理（按 name + frps_server_id 判断），将完全覆盖更新。
    对于不存在的代理，将创建新记录。
    """
    # 验证服务器是否存在
    server = db.query(FrpsServer).filter(FrpsServer.id == frps_server_id).first()
    if not server:
        raise HTTPException(status_code=404, detail="服务器不存在")
    
    # 获取文件扩展名
    filename = file.filename or ""
    file_extension = os.path.splitext(filename)[1].lower()
    
    if file_extension not in ['.ini', '.toml']:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的文件格式: {file_extension}，仅支持 .ini 和 .toml 文件"
        )
    
    # 读取文件内容
    try:
        content = await file.read()
        content_str = content.decode('utf-8')
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"读取文件失败: {str(e)}")
    
    # 解析配置文件
    try:
        parser = ConfigParser()
        proxy_configs = parser.parse_config(content_str, file_extension)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    if not proxy_configs:
        raise HTTPException(status_code=400, detail="配置文件中没有找到有效的代理配置")
    
    # 导入统计
    stats = {
        "total": len(proxy_configs),
        "created": 0,
        "updated": 0,
        "failed": 0,
        "errors": []
    }
    
    port_service = PortService(db)
    
    # 处理每个代理配置
    for proxy_config in proxy_configs:
        try:
            proxy_name = proxy_config['name']
            
            # 检查代理是否已存在
            existing_proxy = db.query(Proxy).filter(
                Proxy.frps_server_id == frps_server_id,
                Proxy.name == proxy_name
            ).first()
            
            # 确定分组名称：优先使用用户指定的分组，否则自动解析
            proxy_group_name = group_name if group_name else Proxy.parse_group_name(proxy_name)
            
            if existing_proxy:
                # 完全覆盖更新现有代理
                old_remote_port = existing_proxy.remote_port
                
                # 如果远程端口发生变化，需要释放旧端口并分配新端口
                new_remote_port = proxy_config.get('remote_port')
                if new_remote_port and old_remote_port != new_remote_port:
                    # 释放旧端口
                    if old_remote_port:
                        try:
                            port_service.release_port(frps_server_id, old_remote_port)
                        except:
                            pass  # 忽略释放失败
                    
                    # 检查新端口是否可用
                    if not port_service.is_port_available(frps_server_id, new_remote_port):
                        stats["failed"] += 1
                        stats["errors"].append({
                            "proxy_name": proxy_name,
                            "error": f"端口 {new_remote_port} 已被占用"
                        })
                        continue
                    
                    # 分配新端口
                    try:
                        port_service.allocate_port(frps_server_id, new_remote_port, proxy_name)
                    except ValueError as e:
                        stats["failed"] += 1
                        stats["errors"].append({
                            "proxy_name": proxy_name,
                            "error": str(e)
                        })
                        continue
                
                # 更新所有字段
                existing_proxy.proxy_type = proxy_config['proxy_type']
                existing_proxy.local_ip = proxy_config['local_ip']
                existing_proxy.local_port = proxy_config['local_port']
                existing_proxy.remote_port = proxy_config.get('remote_port')
                existing_proxy.group_name = proxy_group_name
                existing_proxy.updated_at = datetime.utcnow()
                
                stats["updated"] += 1
                
            else:
                # 创建新代理
                new_remote_port = proxy_config.get('remote_port')
                
                # 如果有远程端口，检查是否可用并分配
                if new_remote_port:
                    if not port_service.is_port_available(frps_server_id, new_remote_port):
                        stats["failed"] += 1
                        stats["errors"].append({
                            "proxy_name": proxy_name,
                            "error": f"端口 {new_remote_port} 已被占用"
                        })
                        continue
                    
                    try:
                        port_service.allocate_port(frps_server_id, new_remote_port, proxy_name)
                    except ValueError as e:
                        stats["failed"] += 1
                        stats["errors"].append({
                            "proxy_name": proxy_name,
                            "error": str(e)
                        })
                        continue
                
                # 创建新代理记录
                new_proxy = Proxy(
                    frps_server_id=frps_server_id,
                    name=proxy_name,
                    group_name=proxy_group_name,
                    proxy_type=proxy_config['proxy_type'],
                    local_ip=proxy_config['local_ip'],
                    local_port=proxy_config['local_port'],
                    remote_port=proxy_config.get('remote_port'),
                    status='offline'  # 默认为离线状态
                )
                
                db.add(new_proxy)
                stats["created"] += 1
        
        except Exception as e:
            stats["failed"] += 1
            stats["errors"].append({
                "proxy_name": proxy_config.get('name', 'unknown'),
                "error": str(e)
            })
    
    # 提交数据库事务
    try:
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"保存数据失败: {str(e)}")
    
    return {
        "success": True,
        "message": f"导入完成：新增 {stats['created']} 个，更新 {stats['updated']} 个，失败 {stats['failed']} 个",
        "stats": stats
    }


@router.post("/import/{format}/{server_name}/{group_name}")
async def import_config_by_names(
    format: str,
    server_name: str,
    group_name: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """直接上传配置文件导入（使用服务器名称和分组名称）
    
    使用示例（curl）:
    ```bash
    # 导入 INI 配置
    curl -u admin:admin -X POST \\
      -H "Content-Type: text/plain" \\
      --data-binary "@frpc.ini" \\
      http://localhost:8000/api/config/import/ini/test_server/test_group
    
    # 导入 TOML 配置
    curl -u admin:admin -X POST \\
      -H "Content-Type: text/plain" \\
      --data-binary "@frpc.toml" \\
      http://localhost:8000/api/config/import/toml/prod_server/production
    ```
    """
    # 验证格式
    if format.lower() not in ['ini', 'toml']:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的格式: {format}，仅支持 ini 和 toml"
        )
    
    # 根据名称查找服务器
    server = db.query(FrpsServer).filter(FrpsServer.name == server_name).first()
    if not server:
        raise HTTPException(status_code=404, detail=f"服务器 '{server_name}' 不存在")
    
    server_id = server.id
    
    # 读取请求体内容
    try:
        content = await request.body()
        content_str = content.decode('utf-8')
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"读取文件失败: {str(e)}")
    
    # 解析配置文件
    try:
        parser = ConfigParser()
        proxy_configs = parser.parse_config(content_str, f".{format}")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    if not proxy_configs:
        raise HTTPException(status_code=400, detail="配置文件中没有找到有效的代理配置")
    
    # 导入统计
    stats = {
        "total": len(proxy_configs),
        "created": 0,
        "updated": 0,
        "failed": 0,
        "errors": []
    }
    
    port_service = PortService(db)
    
    # 处理每个代理配置
    for proxy_config in proxy_configs:
        try:
            proxy_name = proxy_config['name']
            
            # 检查代理是否已存在
            existing_proxy = db.query(Proxy).filter(
                Proxy.frps_server_id == server_id,
                Proxy.name == proxy_name
            ).first()
            
            # 确定分组名称：优先使用用户指定的分组，否则自动解析
            proxy_group_name = group_name if group_name else Proxy.parse_group_name(proxy_name)
            
            if existing_proxy:
                # 完全覆盖更新现有代理
                old_remote_port = existing_proxy.remote_port
                
                # 如果远程端口发生变化，需要释放旧端口并分配新端口
                new_remote_port = proxy_config.get('remote_port')
                if new_remote_port and old_remote_port != new_remote_port:
                    # 释放旧端口
                    if old_remote_port:
                        try:
                            port_service.release_port(server_id, old_remote_port)
                        except:
                            pass  # 忽略释放失败
                    
                    # 检查新端口是否可用
                    if not port_service.is_port_available(server_id, new_remote_port):
                        stats["failed"] += 1
                        stats["errors"].append({
                            "proxy_name": proxy_name,
                            "error": f"端口 {new_remote_port} 已被占用"
                        })
                        continue
                    
                    # 分配新端口
                    try:
                        port_service.allocate_port(server_id, new_remote_port, proxy_name)
                    except ValueError as e:
                        stats["failed"] += 1
                        stats["errors"].append({
                            "proxy_name": proxy_name,
                            "error": str(e)
                        })
                        continue
                
                # 更新所有字段
                existing_proxy.proxy_type = proxy_config['proxy_type']
                existing_proxy.local_ip = proxy_config['local_ip']
                existing_proxy.local_port = proxy_config['local_port']
                existing_proxy.remote_port = proxy_config.get('remote_port')
                existing_proxy.group_name = proxy_group_name
                existing_proxy.updated_at = datetime.utcnow()
                
                stats["updated"] += 1
                
            else:
                # 创建新代理
                new_remote_port = proxy_config.get('remote_port')
                
                # 如果有远程端口，检查是否可用并分配
                if new_remote_port:
                    if not port_service.is_port_available(server_id, new_remote_port):
                        stats["failed"] += 1
                        stats["errors"].append({
                            "proxy_name": proxy_name,
                            "error": f"端口 {new_remote_port} 已被占用"
                        })
                        continue
                    
                    try:
                        port_service.allocate_port(server_id, new_remote_port, proxy_name)
                    except ValueError as e:
                        stats["failed"] += 1
                        stats["errors"].append({
                            "proxy_name": proxy_name,
                            "error": str(e)
                        })
                        continue
                
                # 创建新代理记录
                new_proxy = Proxy(
                    frps_server_id=server_id,
                    name=proxy_name,
                    group_name=proxy_group_name,
                    proxy_type=proxy_config['proxy_type'],
                    local_ip=proxy_config['local_ip'],
                    local_port=proxy_config['local_port'],
                    remote_port=proxy_config.get('remote_port'),
                    status='offline'  # 默认为离线状态
                )
                
                db.add(new_proxy)
                stats["created"] += 1
        
        except Exception as e:
            stats["failed"] += 1
            stats["errors"].append({
                "proxy_name": proxy_config.get('name', 'unknown'),
                "error": str(e)
            })
    
    # 提交数据库事务
    try:
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"保存数据失败: {str(e)}")
    
    return {
        "success": True,
        "message": f"导入完成：新增 {stats['created']} 个，更新 {stats['updated']} 个，失败 {stats['failed']} 个",
        "stats": stats
    }


@router.post("/import/text")
async def import_config_text(
    request: ConfigImportRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """通过JSON提交导入 frpc 配置文件内容
    
    支持 INI 和 TOML 格式的配置文件。
    对于已存在的代理（按 name + frps_server_id 判断），将完全覆盖更新。
    对于不存在的代理，将创建新记录。
    
    使用示例（curl）:
    ```bash
    # 导入 INI 格式配置
    curl -X POST "http://localhost:8000/api/config/import/text" \\
      -H "Authorization: Bearer YOUR_TOKEN" \\
      -H "Content-Type: application/json" \\
      -d '{
        "content": "[ssh]\\ntype = tcp\\nlocal_ip = 127.0.0.1\\nlocal_port = 22\\nremote_port = 6000",
        "format": "ini",
        "frps_server_id": 1,
        "group_name": "default"
      }'
    
    # 或从文件读取内容
    curl -X POST "http://localhost:8000/api/config/import/text" \\
      -H "Authorization: Bearer YOUR_TOKEN" \\
      -H "Content-Type: application/json" \\
      -d @- << EOF
    {
      "content": "$(cat frpc.ini | sed 's/$/\\n/' | tr -d '\\n' | sed 's/\\n/\\\\n/g')",
      "format": "ini",
      "frps_server_id": 1
    }
    EOF
    ```
    """
    # 验证格式
    if request.format.lower() not in ['ini', 'toml']:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的格式: {request.format}，仅支持 ini 和 toml"
        )
    
    # 验证服务器是否存在
    server = db.query(FrpsServer).filter(FrpsServer.id == request.frps_server_id).first()
    if not server:
        raise HTTPException(status_code=404, detail="服务器不存在")
    
    # 解析配置文件
    try:
        parser = ConfigParser()
        proxy_configs = parser.parse_config(request.content, f".{request.format}")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    if not proxy_configs:
        raise HTTPException(status_code=400, detail="配置文件中没有找到有效的代理配置")
    
    # 导入统计
    stats = {
        "total": len(proxy_configs),
        "created": 0,
        "updated": 0,
        "failed": 0,
        "errors": []
    }
    
    port_service = PortService(db)
    
    # 处理每个代理配置
    for proxy_config in proxy_configs:
        try:
            proxy_name = proxy_config['name']
            
            # 检查代理是否已存在
            existing_proxy = db.query(Proxy).filter(
                Proxy.frps_server_id == request.frps_server_id,
                Proxy.name == proxy_name
            ).first()
            
            # 确定分组名称：优先使用用户指定的分组，否则自动解析
            proxy_group_name = request.group_name if request.group_name else Proxy.parse_group_name(proxy_name)
            
            if existing_proxy:
                # 完全覆盖更新现有代理
                old_remote_port = existing_proxy.remote_port
                
                # 如果远程端口发生变化，需要释放旧端口并分配新端口
                new_remote_port = proxy_config.get('remote_port')
                if new_remote_port and old_remote_port != new_remote_port:
                    # 释放旧端口
                    if old_remote_port:
                        try:
                            port_service.release_port(request.frps_server_id, old_remote_port)
                        except:
                            pass  # 忽略释放失败
                    
                    # 检查新端口是否可用
                    if not port_service.is_port_available(request.frps_server_id, new_remote_port):
                        stats["failed"] += 1
                        stats["errors"].append({
                            "proxy_name": proxy_name,
                            "error": f"端口 {new_remote_port} 已被占用"
                        })
                        continue
                    
                    # 分配新端口
                    try:
                        port_service.allocate_port(request.frps_server_id, new_remote_port, proxy_name)
                    except ValueError as e:
                        stats["failed"] += 1
                        stats["errors"].append({
                            "proxy_name": proxy_name,
                            "error": str(e)
                        })
                        continue
                
                # 更新所有字段
                existing_proxy.proxy_type = proxy_config['proxy_type']
                existing_proxy.local_ip = proxy_config['local_ip']
                existing_proxy.local_port = proxy_config['local_port']
                existing_proxy.remote_port = proxy_config.get('remote_port')
                existing_proxy.group_name = proxy_group_name
                existing_proxy.updated_at = datetime.utcnow()
                
                stats["updated"] += 1
                
            else:
                # 创建新代理
                new_remote_port = proxy_config.get('remote_port')
                
                # 如果有远程端口，检查是否可用并分配
                if new_remote_port:
                    if not port_service.is_port_available(request.frps_server_id, new_remote_port):
                        stats["failed"] += 1
                        stats["errors"].append({
                            "proxy_name": proxy_name,
                            "error": f"端口 {new_remote_port} 已被占用"
                        })
                        continue
                    
                    try:
                        port_service.allocate_port(request.frps_server_id, new_remote_port, proxy_name)
                    except ValueError as e:
                        stats["failed"] += 1
                        stats["errors"].append({
                            "proxy_name": proxy_name,
                            "error": str(e)
                        })
                        continue
                
                # 创建新代理记录
                new_proxy = Proxy(
                    frps_server_id=request.frps_server_id,
                    name=proxy_name,
                    group_name=proxy_group_name,
                    proxy_type=proxy_config['proxy_type'],
                    local_ip=proxy_config['local_ip'],
                    local_port=proxy_config['local_port'],
                    remote_port=proxy_config.get('remote_port'),
                    status='offline'  # 默认为离线状态
                )
                
                db.add(new_proxy)
                stats["created"] += 1
        
        except Exception as e:
            stats["failed"] += 1
            stats["errors"].append({
                "proxy_name": proxy_config.get('name', 'unknown'),
                "error": str(e)
            })
    
    # 提交数据库事务
    try:
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"保存数据失败: {str(e)}")
    
    return {
        "success": True,
        "message": f"导入完成：新增 {stats['created']} 个，更新 {stats['updated']} 个，失败 {stats['failed']} 个",
        "stats": stats
    }

