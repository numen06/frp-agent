"""添加代理分组字段"""
import sys
import os

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from sqlalchemy import text
from app.database import engine


def upgrade():
    """添加 group_name 字段到 proxies 表"""
    with engine.connect() as conn:
        # 添加 group_name 字段
        conn.execute(text("""
            ALTER TABLE proxies 
            ADD COLUMN group_name VARCHAR(50)
        """))
        
        # 创建索引
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_proxies_group_name 
            ON proxies(group_name)
        """))
        
        # 从现有代理名称中解析并填充 group_name
        conn.execute(text("""
            UPDATE proxies 
            SET group_name = CASE 
                WHEN name LIKE '%_%' THEN 
                    CASE 
                        WHEN SUBSTR(name, 1, INSTR(name, '_') - 1) != '' THEN SUBSTR(name, 1, INSTR(name, '_') - 1)
                        ELSE '其他'
                    END
                ELSE '其他'
            END
            WHERE group_name IS NULL
        """))
        
        conn.commit()
        print("✓ 成功添加 group_name 字段并更新现有数据")


def downgrade():
    """回滚：删除 group_name 字段"""
    with engine.connect() as conn:
        # 删除索引
        conn.execute(text("""
            DROP INDEX IF EXISTS idx_proxies_group_name
        """))
        
        # 删除字段
        conn.execute(text("""
            ALTER TABLE proxies 
            DROP COLUMN group_name
        """))
        
        conn.commit()
        print("✓ 成功删除 group_name 字段")


if __name__ == "__main__":
    print("执行数据库迁移：添加代理分组字段")
    upgrade()

