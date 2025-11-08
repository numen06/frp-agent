"""
数据库迁移脚本：添加服务器测试状态字段

运行方式：
python -m app.migrations.add_server_test_fields
"""

from sqlalchemy import create_engine, text
from app.config import get_settings

def migrate():
    """执行迁移"""
    settings = get_settings()
    engine = create_engine(settings.database_url)
    
    with engine.connect() as conn:
        # 检查字段是否已存在
        result = conn.execute(text("PRAGMA table_info(frps_servers)"))
        columns = [row[1] for row in result.fetchall()]
        
        # 添加 last_test_status 字段
        if 'last_test_status' not in columns:
            print("添加 last_test_status 字段...")
            conn.execute(text(
                "ALTER TABLE frps_servers ADD COLUMN last_test_status VARCHAR(20) DEFAULT 'unknown' NOT NULL"
            ))
            conn.commit()
            print("✓ last_test_status 字段添加成功")
        else:
            print("✓ last_test_status 字段已存在")
        
        # 添加 last_test_time 字段
        if 'last_test_time' not in columns:
            print("添加 last_test_time 字段...")
            conn.execute(text(
                "ALTER TABLE frps_servers ADD COLUMN last_test_time DATETIME"
            ))
            conn.commit()
            print("✓ last_test_time 字段添加成功")
        else:
            print("✓ last_test_time 字段已存在")
        
        # 添加 last_test_message 字段
        if 'last_test_message' not in columns:
            print("添加 last_test_message 字段...")
            conn.execute(text(
                "ALTER TABLE frps_servers ADD COLUMN last_test_message VARCHAR(500)"
            ))
            conn.commit()
            print("✓ last_test_message 字段添加成功")
        else:
            print("✓ last_test_message 字段已存在")
    
    print("\n✅ 数据库迁移完成！")

if __name__ == "__main__":
    migrate()

