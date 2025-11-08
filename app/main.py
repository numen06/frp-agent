"""FastAPI 应用入口"""
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from contextlib import asynccontextmanager
import logging

from app.config import get_settings
from app.database import init_db, get_db
from app.routers import frps_server, proxy, port, config, sync, user_settings
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

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(frps_server.router)
app.include_router(proxy.router)
app.include_router(port.router)
app.include_router(config.router)
app.include_router(sync.router)
app.include_router(user_settings.router)

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

# 挂载静态文件
try:
    app.mount("/static", StaticFiles(directory="app/static"), name="static")
except RuntimeError:
    logger.warning("静态文件目录不存在或为空")


@app.get("/", response_class=HTMLResponse)
async def root():
    """首页 - 重定向到登录页"""
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/login")


@app.get("/login", response_class=HTMLResponse)
async def login_page():
    """登录页面"""
    try:
        with open("app/templates/login.html", "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return """
        <html>
        <head><title>登录</title></head>
        <body>
            <h1>登录页面未找到</h1>
            <p>请检查 app/templates/login.html 是否存在</p>
        </body>
        </html>
        """


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard():
    """仪表板页面 - 需要登录"""
    try:
        with open("app/templates/dashboard.html", "r", encoding="utf-8") as f:
            content = f.read()
            # 添加登录检查脚本
            auth_check_script = """
    <script>
        // 检查登录状态
        if (!localStorage.getItem('auth_token')) {
            window.location.href = '/login';
        }
    </script>
"""
            # 在 </head> 标签前插入登录检查脚本
            content = content.replace('</head>', auth_check_script + '</head>')
            return content
    except FileNotFoundError:
        return "<h1>Dashboard template not found</h1>"


@app.get("/logout")
async def logout():
    """退出登录"""
    from fastapi.responses import RedirectResponse
    response = RedirectResponse(url="/login")
    return response


@app.get("/settings", response_class=HTMLResponse)
async def settings_page():
    """用户设置页面"""
    try:
        with open("app/templates/settings.html", "r", encoding="utf-8") as f:
            content = f.read()
            # 添加登录检查脚本
            auth_check_script = """
    <script>
        // 检查登录状态
        if (!localStorage.getItem('auth_token')) {
            window.location.href = '/login';
        }
    </script>
"""
            content = content.replace('</head>', auth_check_script + '</head>')
            return content
    except FileNotFoundError:
        return "<h1>Settings template not found</h1>"


@app.get("/health")
async def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "version": "1.0.0"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=settings.app_debug
    )

