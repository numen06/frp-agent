"""FastAPI 应用入口 - 纯 API 模式"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from contextlib import asynccontextmanager
import logging

from app.config import get_settings
from app.database import init_db, get_db
from app.routers import frps_server, proxy, port, config, sync, user_settings, group, frpc_config, config_import
from app.scheduler import start_scheduler, shutdown_scheduler
from sqlalchemy.orm import Session
from fastapi import Depends

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时初始化数据库
    logger.info("初始化数据库...")
    init_db()
    
    # 启动定时任务
    logger.info("启动定时同步任务...")
    await start_scheduler()
    
    yield
    
    # 关闭时清理资源
    logger.info("关闭定时任务...")
    shutdown_scheduler()


# 创建应用
app = FastAPI(
    title="frp-agent 管理系统",
    description="frp 代理管理系统，提供端口管理、冲突检测、配置生成等功能",
    version="1.0.0",
    lifespan=lifespan,
    docs_url=None,  # 禁用 /docs
    redoc_url=None  # 禁用 /redoc
)

# 配置 CORS - 允许前端访问
# 开发环境允许所有来源，生产环境应配置具体域名
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.app_debug else [
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(frps_server.router)
app.include_router(proxy.router)
app.include_router(port.router)
app.include_router(config.router)
app.include_router(config_import.router)
app.include_router(sync.router)
app.include_router(user_settings.router)
app.include_router(group.router)
app.include_router(frpc_config.router)

# 健康检查端点
@app.get("/api/health")
async def health_check(db: Session = Depends(get_db)):
    """健康检查端点"""
    try:
        # 测试数据库连接
        db.execute("SELECT 1")
        return {
            "status": "healthy",
            "service": "frp-agent",
            "database": "connected"
        }
    except Exception as e:
        logger.error(f"健康检查失败: {e}")
        return {
            "status": "unhealthy",
            "service": "frp-agent",
            "database": "disconnected",
            "error": str(e)
        }

# 根路径健康检查（用于前端路由）
@app.get("/")
async def root():
    """API 根路径"""
    return {
        "service": "frp-agent API",
        "version": "1.0.0",
        "status": "running"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=settings.app_debug
    )

