"""创建 API Keys 表的数据库迁移"""
from sqlalchemy import text
from app.database import engine


def upgrade():
    """创建 api_keys 表"""
    with engine.connect() as conn:
        # 创建 api_keys 表
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS api_keys (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key VARCHAR(64) NOT NULL UNIQUE,
                description VARCHAR(200) NOT NULL,
                expires_at TIMESTAMP,
                is_active BOOLEAN NOT NULL DEFAULT 1,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                last_used_at TIMESTAMP
            )
        """))
        
        # 创建索引
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS ix_api_keys_key ON api_keys(key)
        """))
        
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS ix_api_keys_is_active ON api_keys(is_active)
        """))
        
        conn.commit()
        print("✓ API Keys 表创建成功")


def downgrade():
    """删除 api_keys 表"""
    with engine.connect() as conn:
        conn.execute(text("DROP TABLE IF EXISTS api_keys"))
        conn.commit()
        print("✓ API Keys 表已删除")


if __name__ == "__main__":
    print("正在创建 api_keys 表...")
    upgrade()
    print("迁移完成！")

