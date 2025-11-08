#!/usr/bin/env python3
"""
frp-agent 主入口

直接运行此文件启动应用：
    python app.py

或者使用 uvicorn：
    uvicorn app.main:app --host 0.0.0.0 --port 8000
"""

import os
import sys
import uvicorn
from app.config import get_settings

def main():
    """主函数"""
    # 确保数据目录存在
    os.makedirs("data", exist_ok=True)
    
    settings = get_settings()
    
    print("=" * 50)
    print("🚀 frp-agent 管理系统")
    print("=" * 50)
    print(f"📍 访问地址: http://{settings.app_host}:{settings.app_port}")
    print(f"🎨 管理界面: http://{settings.app_host}:{settings.app_port}/dashboard")
    print(f"👤 默认账号: {settings.auth_username}")
    print("=" * 50)
    print()
    
    # 启动 uvicorn 服务器
    uvicorn.run(
        "app.main:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=settings.app_debug,
        log_level="info"
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

