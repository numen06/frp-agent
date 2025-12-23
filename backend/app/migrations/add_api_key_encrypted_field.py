"""
数据库迁移脚本：添加 API Key 加密字段

运行方式：
python -m app.migrations.add_api_key_encrypted_field
"""

from sqlalchemy import create_engine, text
from app.config import get_settings

def migrate():
    """执行迁移"""
    settings = get_settings()
    engine = create_engine(settings.database_url)
    
    with engine.connect() as conn:
        # 检查字段是否已存在
        result = conn.execute(text("PRAGMA table_info(api_keys)"))
        columns = [row[1] for row in result.fetchall()]
        
        # 添加 key_encrypted 字段
        if 'key_encrypted' not in columns:
            print("添加 key_encrypted 字段...")
            conn.execute(text(
                "ALTER TABLE api_keys ADD COLUMN key_encrypted TEXT"
            ))
            conn.commit()
            print("✓ key_encrypted 字段添加成功")
        else:
            print("✓ key_encrypted 字段已存在")
    
    print("\n✅ 数据库迁移完成！")

if __name__ == "__main__":
    migrate()

