#!/usr/bin/env python3
"""
frp-agent 启动脚本（辅助脚本，从项目根目录运行）

这是从项目根目录启动应用的辅助脚本。
主入口文件是 backend/app.py，推荐直接使用主入口文件。

使用方法：
    python run.py

或者直接使用主入口文件（推荐）：
    cd backend
    python app.py

或者：
    python backend/app.py
"""

import os
import sys
import uvicorn

# 获取项目根目录
project_root = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.join(project_root, "backend")

# 将 backend 目录添加到 Python 路径
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

# 设置 PYTHONPATH 环境变量，确保 uvicorn 子进程也能找到模块
pythonpath = os.environ.get("PYTHONPATH", "")
if backend_dir not in pythonpath.split(os.pathsep):
    if pythonpath:
        os.environ["PYTHONPATH"] = backend_dir + os.pathsep + pythonpath
    else:
        os.environ["PYTHONPATH"] = backend_dir

# 导入配置和应用
from app.config import get_settings
from app.main import app as fastapi_app


def main():
    """主函数"""
    # 确保数据目录存在
    data_dir = os.path.join(project_root, "data")
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
    # 使用应用对象而不是字符串路径，这样更可靠
    # 如果需要 reload，使用 reload_dirs 参数
    if settings.app_debug:
        uvicorn.run(
            fastapi_app,
            host=settings.app_host,
            port=settings.app_port,
            reload=True,
            reload_dirs=[backend_dir],
            log_level="info",
        )
    else:
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
        import traceback

        traceback.print_exc()
        sys.exit(1)
