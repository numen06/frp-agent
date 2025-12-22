"""数据库连接管理"""
import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator

from app.config import get_settings

settings = get_settings()

# 处理 SQLite 数据库路径（确保数据目录存在）
database_url = settings.database_url
if "sqlite" in database_url and ":///" in database_url:
    # 提取文件路径
    db_path = database_url.split(":///")[-1]
    # 如果是相对路径，需要确保目录存在
    if not os.path.isabs(db_path):
        # 获取项目根目录（backend/app 的父目录的父目录）
        # database.py 在 backend/app/database.py
        current_file = os.path.abspath(__file__)  # backend/app/database.py
        app_dir = os.path.dirname(current_file)    # backend/app
        backend_dir = os.path.dirname(app_dir)     # backend
        project_root = os.path.dirname(backend_dir)  # 项目根目录
        # 规范化路径（处理 ./ 和 ../）
        db_path_normalized = os.path.normpath(db_path)
        # 构建完整路径
        full_db_path = os.path.join(project_root, db_path_normalized)
        # 确保数据目录存在
        db_dir = os.path.dirname(full_db_path)
        os.makedirs(db_dir, exist_ok=True)
        # 更新数据库 URL（Windows 路径需要特殊处理）
        if os.name == 'nt':  # Windows
            # Windows 路径需要转换为正斜杠或使用绝对路径
            full_db_path = full_db_path.replace('\\', '/')
        database_url = f"sqlite:///{full_db_path}"

# 创建数据库引擎
engine = create_engine(
    database_url,
    connect_args={"check_same_thread": False} if "sqlite" in database_url else {}
)

# 创建会话工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 创建基类
Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """获取数据库会话"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """初始化数据库"""
    Base.metadata.create_all(bind=engine)

