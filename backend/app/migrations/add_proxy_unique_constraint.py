"""添加代理表唯一约束：同一服务器下代理名称不能重复"""
import sys
import os

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from sqlalchemy import text
from app.database import engine


def upgrade():
    """先清理重复数据，再添加唯一约束"""
    with engine.connect() as conn:
        # 1. 清理重复记录：每组 (frps_server_id, name) 保留 id 最大的一条
        # SQLite 在 DELETE 的子查询中不能直接引用同一表，使用临时表
        conn.execute(text("DROP TABLE IF EXISTS proxies_keep"))
        conn.execute(text("""
            CREATE TEMP TABLE proxies_keep AS
            SELECT MAX(id) as id FROM proxies GROUP BY frps_server_id, name
        """))
        conn.execute(text("""
            DELETE FROM proxies WHERE id NOT IN (SELECT id FROM proxies_keep)
        """))
        conn.execute(text("DROP TABLE IF EXISTS proxies_keep"))
        
        # 2. 添加唯一约束（SQLite 使用 CREATE UNIQUE INDEX）
        conn.execute(text("""
            CREATE UNIQUE INDEX IF NOT EXISTS uq_proxy_server_name
            ON proxies(frps_server_id, name)
        """))
        
        conn.commit()
        print("[OK] 成功清理重复代理并添加唯一约束 (frps_server_id, name)")


def downgrade():
    """移除唯一约束"""
    with engine.connect() as conn:
        conn.execute(text("DROP INDEX IF EXISTS uq_proxy_server_name"))
        conn.commit()
        print("[OK] 已移除 proxies 表唯一约束")


if __name__ == "__main__":
    print("执行数据库迁移：添加代理唯一约束")
    upgrade()
    print("迁移完成！")
