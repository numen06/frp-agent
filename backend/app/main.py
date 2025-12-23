"""FastAPI 应用入口 - API + Vue 前端模式

后端提供 RESTful API，前端由 Vue + Vite 构建，构建后的静态文件由 FastAPI 服务。
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from contextlib import asynccontextmanager
import logging
import os

from app.config import get_settings
from app.database import init_db, get_db
from app.routers import frps_server, proxy, port, config, sync, user_settings, group, frpc_config, config_import, api_key
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
app.include_router(api_key.router)

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

# 配置静态文件服务（前端构建文件）
# 检测 dist 目录位置：Docker 环境在 /app/dist，本地开发在项目根目录的 dist
current_file = os.path.abspath(__file__)
current_dir = os.path.dirname(current_file)

# 尝试多个可能的 dist 目录路径
possible_dist_dirs = [
    "/app/dist",  # Docker 环境
    os.path.join(os.path.dirname(os.path.dirname(current_dir)), "dist"),  # 项目根目录的 dist
]

dist_dir = None
for possible_dir in possible_dist_dirs:
    if os.path.exists(possible_dir) and os.path.isdir(possible_dir):
        dist_dir = possible_dir
        break

# 定义前端 index.html 路径
index_path = os.path.join(dist_dir, "index.html") if dist_dir and os.path.exists(dist_dir) else None

# 如果 dist 目录存在，配置静态文件服务
if dist_dir and os.path.exists(dist_dir) and os.path.exists(index_path):
    logger.info(f"前端构建目录已找到: {dist_dir}")
    
    # 挂载静态资源目录（JS、CSS、图片等）
    assets_dir = os.path.join(dist_dir, "assets")
    if os.path.exists(assets_dir):
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")
    
    # 根路径返回前端 index.html
    @app.get("/")
    async def root():
        """返回前端页面"""
        return FileResponse(index_path)
    
    # Catch-all 路由：所有非 API 路径都返回 index.html（用于 Vue Router 的 history 模式）
    # 注意：这个路由必须在最后注册，因为它会匹配所有路径
    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        """处理前端路由，所有非 API 路径返回 index.html"""
        # 排除 API 路径
        if full_path.startswith("api/"):
            return {"error": "Not found"}
        
        # 排除静态资源路径（这些应该由 StaticFiles 处理）
        if full_path.startswith("assets/"):
            return {"error": "Not found"}
        
        # 检查是否是根目录下的静态文件请求（如 favicon.svg）
        static_file_path = os.path.join(dist_dir, full_path)
        if os.path.exists(static_file_path) and os.path.isfile(static_file_path) and full_path != "index.html":
            return FileResponse(static_file_path)
        
        # 返回前端 index.html（用于 Vue Router）
        return FileResponse(index_path)
else:
    # dist 目录不存在，返回 API 信息
    logger.warning(f"前端构建目录未找到，已尝试的路径: {possible_dist_dirs}")
    
    @app.get("/")
    async def root():
        """API 根路径"""
        return {
            "service": "frp-agent API",
            "version": "1.0.0",
            "status": "running",
            "note": "前端文件未构建"
        }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=settings.app_debug
    )

