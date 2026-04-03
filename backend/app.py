#!/usr/bin/env python3
"""
frp-agent 主入口文件

这是 frp-agent 后端服务的主入口文件，支持多种运行方式：

1. 从 backend 目录运行（推荐）：
   cd backend
   python app.py

2. 从项目根目录运行：
   python backend/app.py

3. 使用 uvicorn 直接运行（需要在 backend 目录下）：
   cd backend
   uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

注意：此文件会自动检测运行环境（本地开发/Docker），并设置正确的路径和配置。
"""

import os
import sys
import uvicorn

# 检测运行环境并设置正确的导入路径
# Docker 环境：app.py 在 /app/，backend 目录在 /app/backend/
# 本地开发：app.py 在 backend/，可以直接导入 app
current_file = os.path.abspath(__file__)
current_dir = os.path.dirname(current_file)
current_basename = os.path.basename(current_dir)

# 如果当前目录名是 backend，说明是本地开发环境
# 如果当前目录名不是 backend，可能是 Docker 环境（app.py 在 /app/）
if current_basename == "backend":
    # 本地开发：在 backend 目录下，可以直接导入 app
    # 确保 backend 目录在 Python 路径中
    if current_dir not in sys.path:
        sys.path.insert(0, current_dir)
    app_module_path = "app"
    # 设置 PYTHONPATH 环境变量，确保 uvicorn 子进程也能找到模块
    pythonpath = os.environ.get("PYTHONPATH", "")
    if current_dir not in pythonpath.split(os.pathsep):
        if pythonpath:
            os.environ["PYTHONPATH"] = current_dir + os.pathsep + pythonpath
        else:
            os.environ["PYTHONPATH"] = current_dir
else:
    # Docker 环境：app.py 在 /app/，backend 在 /app/backend/
    backend_dir = os.path.join(current_dir, "backend")
    if backend_dir not in sys.path:
        sys.path.insert(0, backend_dir)
    app_module_path = "app"
    # 设置 PYTHONPATH 环境变量
    pythonpath = os.environ.get("PYTHONPATH", "")
    if backend_dir not in pythonpath.split(os.pathsep):
        if pythonpath:
            os.environ["PYTHONPATH"] = backend_dir + os.pathsep + pythonpath
        else:
            os.environ["PYTHONPATH"] = backend_dir

# 导入配置和应用对象
from app.config import get_settings
from app.main import app as fastapi_app


def main():
    """主函数"""
    # 确定数据目录位置
    # Docker 环境：数据目录在 /app/data/
    # 本地开发：数据目录在项目根目录的 data/
    if current_basename == "backend":
        # 本地开发：数据目录在项目根目录
        project_root = os.path.dirname(current_dir)
        data_dir = os.path.join(project_root, "data")
    else:
        # Docker 环境：数据目录在当前目录下
        data_dir = os.path.join(current_dir, "data")

    os.makedirs(data_dir, exist_ok=True)

    settings = get_settings()

    print("=" * 50)
    print("🚀 frp-agent API 服务")
    print("=" * 50)
    print(f"📍 API 地址: http://{settings.app_host}:{settings.app_port}")
    print(f"👤 默认账号: {settings.auth_username}")
    print("=" * 50)
    print()

    # 启动 uvicorn 服务器
    # 直接使用应用对象而不是字符串路径，这样更可靠
    # 使用 reload_dirs 参数指定需要监控的目录
    if settings.app_debug:
        # reload 模式：使用 reload_dirs 指定监控目录
        uvicorn.run(
            fastapi_app,
            host=settings.app_host,
            port=settings.app_port,
            reload=True,
            reload_dirs=(
                [current_dir]
                if current_basename == "backend"
                else [os.path.join(current_dir, "backend")]
            ),
            log_level="info",
        )
    else:
        # 非 reload 模式：直接运行
        uvicorn.run(
            fastapi_app,
            host=settings.app_host,
            port=settings.app_port,
            reload=False,
            log_level="info",
        )


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 服务已停止")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ 启动失败: {e}")
        sys.exit(1)
