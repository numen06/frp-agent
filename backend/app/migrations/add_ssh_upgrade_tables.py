"""SSH 客户端升级相关表迁移"""
from sqlalchemy import text
from app.database import engine


def upgrade():
    with engine.connect() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS ssh_credentials (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name VARCHAR(100) NOT NULL,
                username VARCHAR(100) NOT NULL,
                auth_type VARCHAR(20) NOT NULL,
                password_encrypted TEXT,
                private_key_encrypted TEXT,
                passphrase_encrypted TEXT,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS proxy_ssh_states (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                proxy_id INTEGER NOT NULL UNIQUE,
                credential_id INTEGER,
                install_path VARCHAR(500),
                is_ssh_candidate BOOLEAN NOT NULL DEFAULT 0,
                reachable BOOLEAN,
                platform VARCHAR(50),
                current_version VARCHAR(100),
                target_version VARCHAR(50),
                target_package_id INTEGER,
                upgradeable BOOLEAN NOT NULL DEFAULT 0,
                status VARCHAR(50) NOT NULL DEFAULT 'unknown',
                message TEXT,
                last_scanned_at TIMESTAMP,
                last_upgraded_at TIMESTAMP,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (proxy_id) REFERENCES proxies(id),
                FOREIGN KEY (credential_id) REFERENCES ssh_credentials(id),
                FOREIGN KEY (target_package_id) REFERENCES frp_packages(id)
            )
        """))
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS ix_proxy_ssh_states_proxy_id
            ON proxy_ssh_states(proxy_id)
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS client_upgrade_jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_type VARCHAR(20) NOT NULL,
                scope_type VARCHAR(20) NOT NULL,
                frps_server_id INTEGER,
                group_name VARCHAR(50),
                proxy_id INTEGER,
                credential_id INTEGER,
                status VARCHAR(30) NOT NULL DEFAULT 'queued',
                total_count INTEGER NOT NULL DEFAULT 0,
                success_count INTEGER NOT NULL DEFAULT 0,
                failed_count INTEGER NOT NULL DEFAULT 0,
                skipped_count INTEGER NOT NULL DEFAULT 0,
                summary TEXT,
                result_json TEXT,
                error_message TEXT,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                started_at TIMESTAMP,
                finished_at TIMESTAMP,
                FOREIGN KEY (frps_server_id) REFERENCES frps_servers(id),
                FOREIGN KEY (proxy_id) REFERENCES proxies(id),
                FOREIGN KEY (credential_id) REFERENCES ssh_credentials(id)
            )
        """))
        conn.commit()
        print("✓ SSH 升级相关表创建成功")


def downgrade():
    with engine.connect() as conn:
        conn.execute(text("DROP TABLE IF EXISTS client_upgrade_jobs"))
        conn.execute(text("DROP TABLE IF EXISTS proxy_ssh_states"))
        conn.execute(text("DROP TABLE IF EXISTS ssh_credentials"))
        conn.commit()
        print("✓ SSH 升级相关表已删除")


if __name__ == "__main__":
    upgrade()
