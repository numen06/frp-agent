"""FRP 流量快照及主机连接字节计数；旧数据保持 NULL，表示尚未采集。"""
from sqlalchemy import inspect, text

from app.database import engine


def upgrade():
    fields = {
        "proxies": {
            "today_traffic_in": "BIGINT",
            "today_traffic_out": "BIGINT",
            "cur_conns": "INTEGER",
            "traffic_updated_at": "DATETIME",
        },
        "host_audit_logs": {"bytes_sent": "BIGINT", "bytes_received": "BIGINT"},
    }
    with engine.begin() as conn:
        for table, columns in fields.items():
            existing = {column["name"] for column in inspect(conn).get_columns(table)}
            for name, sql_type in columns.items():
                if name not in existing:
                    conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {name} {sql_type}"))


if __name__ == "__main__":
    upgrade()
