"""
数据库迁移脚本：添加 FRP 版本相关字段

运行方式：
python -m app.migrations.add_frp_version_fields
"""

from sqlalchemy import text
from app.database import engine


def upgrade():
    """添加 frps_servers / proxies 版本相关列（幂等）"""
    with engine.connect() as conn:
        result = conn.execute(text("PRAGMA table_info(frps_servers)"))
        server_columns = [row[1] for row in result.fetchall()]

        if "server_version" not in server_columns:
            print("添加 server_version 字段...")
            conn.execute(text(
                "ALTER TABLE frps_servers ADD COLUMN server_version VARCHAR(50)"
            ))
            conn.commit()
            print("✓ server_version 字段添加成功")
        else:
            print("✓ server_version 字段已存在")

        if "last_version_check_time" not in server_columns:
            print("添加 last_version_check_time 字段...")
            conn.execute(text(
                "ALTER TABLE frps_servers ADD COLUMN last_version_check_time DATETIME"
            ))
            conn.commit()
            print("✓ last_version_check_time 字段添加成功")
        else:
            print("✓ last_version_check_time 字段已存在")

        if "last_version_check_message" not in server_columns:
            print("添加 last_version_check_message 字段...")
            conn.execute(text(
                "ALTER TABLE frps_servers ADD COLUMN last_version_check_message VARCHAR(500)"
            ))
            conn.commit()
            print("✓ last_version_check_message 字段添加成功")
        else:
            print("✓ last_version_check_message 字段已存在")

        result = conn.execute(text("PRAGMA table_info(proxies)"))
        proxy_columns = [row[1] for row in result.fetchall()]

        if "client_version" not in proxy_columns:
            print("添加 client_version 字段...")
            conn.execute(text(
                "ALTER TABLE proxies ADD COLUMN client_version VARCHAR(50)"
            ))
            conn.commit()
            print("✓ client_version 字段添加成功")
        else:
            print("✓ client_version 字段已存在")

    print("\n✅ 数据库迁移完成！")


def migrate():
    """兼容旧调用名"""
    upgrade()


if __name__ == "__main__":
    upgrade()
