"""创建分组表的数据库迁移"""
from sqlalchemy import text
from app.database import engine


def upgrade():
    """创建 groups 表"""
    with engine.connect() as conn:
        # 创建 groups 表
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS groups (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                frps_server_id INTEGER NOT NULL,
                name VARCHAR(50) NOT NULL,
                description VARCHAR(200),
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (frps_server_id) REFERENCES frps_servers(id) ON DELETE CASCADE,
                UNIQUE (frps_server_id, name)
            )
        """))
        
        # 创建索引
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS ix_groups_frps_server_id ON groups(frps_server_id)
        """))
        
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS ix_groups_name ON groups(name)
        """))
        
        conn.commit()
        print("✓ Groups 表创建成功")


def downgrade():
    """删除 groups 表"""
    with engine.connect() as conn:
        conn.execute(text("DROP TABLE IF EXISTS groups"))
        conn.commit()
        print("✓ Groups 表已删除")


if __name__ == "__main__":
    print("正在创建 groups 表...")
    upgrade()
    print("迁移完成！")

