"""添加 auth_token 字段到 frps_servers 表"""
from sqlalchemy import Column, String, text
from app.database import engine


def upgrade():
    """添加 auth_token 字段"""
    with engine.connect() as conn:
        # 检查列是否已存在
        result = conn.execute(text(
            "SELECT COUNT(*) FROM pragma_table_info('frps_servers') WHERE name='auth_token'"
        ))
        exists = result.scalar() > 0
        
        if not exists:
            print("添加 auth_token 字段到 frps_servers 表...")
            conn.execute(text(
                "ALTER TABLE frps_servers ADD COLUMN auth_token VARCHAR(255)"
            ))
            conn.commit()
            print("✓ auth_token 字段添加成功")
        else:
            print("auth_token 字段已存在，跳过")


def downgrade():
    """回滚：删除 auth_token 字段"""
    with engine.connect() as conn:
        # SQLite 不支持直接删除列，需要重建表
        print("警告：SQLite 不支持直接删除列，需要手动处理")


if __name__ == "__main__":
    upgrade()

