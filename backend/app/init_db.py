"""数据库初始化脚本"""
import sys
from sqlalchemy.orm import Session

from app.database import engine, SessionLocal, Base
from app.models import User, FrpsServer, Proxy, PortAllocation, ProxyHistory, ApiKey
from app.auth import get_password_hash
from app.config import get_settings

settings = get_settings()


def init_database():
    """初始化数据库"""
    print("正在创建数据库表...")
    
    # 创建所有表
    Base.metadata.create_all(bind=engine)
    
    print("✓ 数据库表创建成功")


def create_default_user(db: Session):
    """创建默认管理员账户"""
    # 检查是否已存在管理员账户
    existing_user = db.query(User).filter(User.username == settings.auth_username).first()
    
    if existing_user:
        print(f"管理员账户 '{settings.auth_username}' 已存在")
        return
    
    # 创建默认管理员
    admin_user = User(
        username=settings.auth_username,
        password_hash=get_password_hash(settings.auth_password)
    )
    
    db.add(admin_user)
    db.commit()
    
    print(f"✓ 创建默认管理员账户: {settings.auth_username}")


def create_default_server(db: Session):
    """创建默认 frps 服务器配置"""
    # 检查是否已存在默认服务器
    existing_server = db.query(FrpsServer).filter(
        FrpsServer.name == settings.default_frps_name
    ).first()
    
    if existing_server:
        print(f"默认服务器 '{settings.default_frps_name}' 已存在")
        return
    
    # 创建默认服务器
    default_server = FrpsServer(
        name=settings.default_frps_name,
        server_addr=settings.default_frps_server_addr,
        server_port=settings.default_frps_server_port,
        api_base_url=settings.default_frps_api_base_url,
        auth_username=settings.default_frps_auth_username,
        auth_password=settings.default_frps_auth_password,
        is_active=True
    )
    
    db.add(default_server)
    db.commit()
    
    print(f"✓ 创建默认服务器配置: {settings.default_frps_name}")


def main():
    """主函数"""
    print("=" * 50)
    print("frp-agent 数据库初始化")
    print("=" * 50)
    
    try:
        # 初始化数据库
        init_database()
        
        # 创建数据库会话
        db = SessionLocal()
        
        try:
            # 创建默认用户
            create_default_user(db)
            
            # 创建默认服务器
            create_default_server(db)
            
            print("\n" + "=" * 50)
            print("初始化完成！")
            print("=" * 50)
            print(f"\n默认登录信息:")
            print(f"  用户名: {settings.auth_username}")
            print(f"  密码: {settings.auth_password}")
            print(f"\n访问地址: http://{settings.app_host}:{settings.app_port}")
            print(f"管理界面: http://{settings.app_host}:{settings.app_port}/dashboard")
            print(f"API 文档: http://{settings.app_host}:{settings.app_port}/docs")
            
        finally:
            db.close()
            
    except Exception as e:
        print(f"\n❌ 初始化失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

