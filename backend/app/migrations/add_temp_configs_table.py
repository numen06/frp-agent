"""添加临时配置表"""
from sqlalchemy import text
from app.database import engine


def upgrade():
    """创建临时配置表"""
    with engine.connect() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS temp_configs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                config_id VARCHAR(50) UNIQUE NOT NULL,
                server_name VARCHAR(100) NOT NULL,
                group_name VARCHAR(100) NOT NULL,
                config_content TEXT NOT NULL,
                format VARCHAR(10) NOT NULL DEFAULT 'ini',
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP NOT NULL
            )
        """))
        
        # 创建索引
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_temp_configs_config_id 
            ON temp_configs(config_id)
        """))
        
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_temp_configs_expires_at 
            ON temp_configs(expires_at)
        """))
        
        conn.commit()
        print("✓ 临时配置表创建成功")


def downgrade():
    """删除临时配置表"""
    with engine.connect() as conn:
        conn.execute(text("DROP TABLE IF EXISTS temp_configs"))
        conn.commit()
        print("✓ 临时配置表已删除")


if __name__ == "__main__":
    print("正在创建临时配置表...")
    upgrade()

