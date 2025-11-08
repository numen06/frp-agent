"""定时任务调度器"""
import asyncio
import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy.orm import Session
from datetime import datetime
import json

from app.database import SessionLocal
from app.config import get_settings
from app.models.frps_server import FrpsServer
from app.models.proxy import Proxy
from app.models.history import ProxyHistory
from app.frps_client import FrpsClient
from app.services.port_service import PortService

logger = logging.getLogger(__name__)
settings = get_settings()

# 全局调度器实例
scheduler: AsyncIOScheduler = None


async def sync_all_servers():
    """同步所有活跃的 frps 服务器"""
    db: Session = SessionLocal()
    
    try:
        # 获取所有活跃的服务器
        servers = db.query(FrpsServer).filter(FrpsServer.is_active == True).all()
        
        if not servers:
            logger.info("没有活跃的 frps 服务器需要同步")
            return
        
        logger.info(f"开始同步 {len(servers)} 个 frps 服务器...")
        
        for server in servers:
            try:
                await sync_server(db, server)
            except Exception as e:
                logger.error(f"同步服务器 {server.name} 失败: {e}")
        
        logger.info("所有服务器同步完成")
        
    except Exception as e:
        logger.error(f"同步任务失败: {e}")
    finally:
        db.close()


async def sync_server(db: Session, server: FrpsServer):
    """同步单个服务器的代理状态
    
    Args:
        db: 数据库会话
        server: frps 服务器配置
    """
    logger.info(f"同步服务器: {server.name}")
    
    # 创建客户端
    client = FrpsClient(server)
    
    # 获取所有代理
    all_proxies_data = await client.get_all_proxies()
    
    # 合并所有类型的代理
    all_proxies = []
    for proxy_type, proxies in all_proxies_data.items():
        for proxy_data in proxies:
            parsed = client.parse_proxy_info(proxy_data)
            parsed["proxy_type"] = proxy_type
            all_proxies.append(parsed)
    
    logger.info(f"从 {server.name} 获取到 {len(all_proxies)} 个代理")
    
    # 获取数据库中的所有代理
    db_proxies = db.query(Proxy).filter(Proxy.frps_server_id == server.id).all()
    db_proxy_map = {proxy.name: proxy for proxy in db_proxies}
    
    # 更新或创建代理
    active_proxy_names = set()
    for proxy_info in all_proxies:
        proxy_name = proxy_info["name"]
        active_proxy_names.add(proxy_name)
        
        if proxy_name in db_proxy_map:
            # 更新现有代理
            db_proxy = db_proxy_map[proxy_name]
            old_status = db_proxy.status
            db_proxy.status = proxy_info["status"]
            db_proxy.remote_port = proxy_info["remote_port"]
            
            # 如果状态从离线变为在线，记录历史
            if old_status == "offline" and proxy_info["status"] == "online":
                history = ProxyHistory(
                    frps_server_id=server.id,
                    proxy_name=proxy_name,
                    action="online",
                    timestamp=datetime.utcnow(),
                    details=json.dumps(proxy_info)
                )
                db.add(history)
                logger.info(f"代理 {proxy_name} 上线")
        else:
            # 发现新代理
            new_proxy = Proxy(
                frps_server_id=server.id,
                name=proxy_name,
                proxy_type=proxy_info["proxy_type"],
                remote_port=proxy_info["remote_port"],
                local_ip=proxy_info["local_ip"],
                local_port=0,
                status=proxy_info["status"]
            )
            db.add(new_proxy)
            
            history = ProxyHistory(
                frps_server_id=server.id,
                proxy_name=proxy_name,
                action="discovered",
                timestamp=datetime.utcnow(),
                details=json.dumps(proxy_info)
            )
            db.add(history)
            logger.info(f"发现新代理 {proxy_name}")
    
    # 标记不在活跃列表中的代理为离线
    for proxy_name, db_proxy in db_proxy_map.items():
        if proxy_name not in active_proxy_names and db_proxy.status == "online":
            db_proxy.status = "offline"
            
            history = ProxyHistory(
                frps_server_id=server.id,
                proxy_name=proxy_name,
                action="offline",
                timestamp=datetime.utcnow(),
                details=json.dumps({"reason": "not_found_in_sync"})
            )
            db.add(history)
            logger.warning(f"代理 {proxy_name} 下线")
    
    # 检测冲突
    port_service = PortService(db)
    conflicts = port_service.detect_conflicts(server.id, all_proxies)
    
    if conflicts:
        logger.warning(f"检测到 {len(conflicts)} 个端口冲突")
        for conflict in conflicts:
            # 记录冲突
            history = ProxyHistory(
                frps_server_id=server.id,
                proxy_name=conflict.get("proxy_name", "unknown"),
                action="conflict",
                timestamp=datetime.utcnow(),
                details=json.dumps(conflict)
            )
            db.add(history)
    
    db.commit()


async def cleanup_expired_temp_configs():
    """清理过期的临时配置"""
    db: Session = SessionLocal()
    
    try:
        from app.models.temp_config import TempConfig
        
        # 删除所有过期的临时配置
        expired_count = db.query(TempConfig).filter(
            TempConfig.expires_at < datetime.utcnow()
        ).delete()
        
        db.commit()
        
        if expired_count > 0:
            logger.info(f"已清理 {expired_count} 个过期的临时配置")
        
    except Exception as e:
        logger.error(f"清理过期临时配置失败: {e}")
        db.rollback()
    finally:
        db.close()


async def start_scheduler():
    """启动调度器"""
    global scheduler
    
    scheduler = AsyncIOScheduler()
    
    # 添加定时同步任务
    scheduler.add_job(
        sync_all_servers,
        trigger=IntervalTrigger(seconds=settings.sync_interval_seconds),
        id="sync_all_servers",
        name="同步所有 frps 服务器",
        replace_existing=True
    )
    
    # 添加清理过期临时配置任务（每小时一次）
    scheduler.add_job(
        cleanup_expired_temp_configs,
        trigger=IntervalTrigger(hours=1),
        id="cleanup_temp_configs",
        name="清理过期的临时配置",
        replace_existing=True
    )
    
    scheduler.start()
    logger.info(f"定时同步任务已启动，间隔: {settings.sync_interval_seconds} 秒")
    logger.info("临时配置清理任务已启动，间隔: 1 小时")
    
    # 立即执行一次同步
    await sync_all_servers()


def shutdown_scheduler():
    """关闭调度器"""
    global scheduler
    
    if scheduler and scheduler.running:
        scheduler.shutdown()
        logger.info("定时任务调度器已关闭")

