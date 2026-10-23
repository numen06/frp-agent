"""标记由本程序管理的内置 frps 服务器记录。"""
from sqlalchemy import inspect, text

from app.database import engine


def upgrade():
    with engine.begin() as conn:
        if "is_builtin" not in {column["name"] for column in inspect(conn).get_columns("frps_servers")}:
            conn.execute(text("ALTER TABLE frps_servers ADD COLUMN is_builtin BOOLEAN NOT NULL DEFAULT 0"))
        if "raw_config_encrypted" not in {column["name"] for column in inspect(conn).get_columns("builtin_frps_config")}:
            conn.execute(text("ALTER TABLE builtin_frps_config ADD COLUMN raw_config_encrypted TEXT"))
