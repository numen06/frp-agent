"""增加主机管理、访问授权、审计表以及用户角色字段。"""
from sqlalchemy import text

from app.database import engine


def _columns(conn, table_name):
    result = conn.execute(text(f"PRAGMA table_info({table_name})"))
    return {row[1] for row in result.fetchall()}


def upgrade():
    with engine.connect() as conn:
        user_columns = _columns(conn, "users")
        if "role" not in user_columns:
            conn.execute(text(
                "ALTER TABLE users ADD COLUMN role VARCHAR(20) NOT NULL DEFAULT 'admin'"
            ))
        if "is_active" not in user_columns:
            conn.execute(text(
                "ALTER TABLE users ADD COLUMN is_active BOOLEAN NOT NULL DEFAULT 1"
            ))

        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS docker_credentials (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name VARCHAR(100) NOT NULL,
                auth_type VARCHAR(20) NOT NULL,
                username VARCHAR(100),
                password_encrypted TEXT,
                api_key_encrypted TEXT,
                ca_cert_encrypted TEXT,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS managed_hosts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name VARCHAR(100) NOT NULL UNIQUE,
                address VARCHAR(255) NOT NULL,
                port INTEGER NOT NULL DEFAULT 22,
                host_type VARCHAR(20) NOT NULL DEFAULT 'ssh',
                credential_id INTEGER,
                docker_credential_id INTEGER,
                docker_use_tls BOOLEAN NOT NULL DEFAULT 1,
                docker_verify_tls BOOLEAN NOT NULL DEFAULT 1,
                docker_endpoint_id INTEGER,
                description TEXT,
                tags VARCHAR(500),
                is_active BOOLEAN NOT NULL DEFAULT 1,
                host_key_fingerprint VARCHAR(100),
                last_status VARCHAR(20) NOT NULL DEFAULT 'unknown',
                last_checked_at TIMESTAMP,
                last_message VARCHAR(500),
                version_info VARCHAR(500),
                created_by_user_id INTEGER,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (credential_id) REFERENCES ssh_credentials(id),
                FOREIGN KEY (docker_credential_id) REFERENCES docker_credentials(id),
                FOREIGN KEY (created_by_user_id) REFERENCES users(id)
            )
        """))
        host_columns = _columns(conn, "managed_hosts")
        if "docker_credential_id" not in host_columns:
            conn.execute(text(
                "ALTER TABLE managed_hosts ADD COLUMN docker_credential_id INTEGER"
            ))
        if "docker_use_tls" not in host_columns:
            conn.execute(text(
                "ALTER TABLE managed_hosts ADD COLUMN docker_use_tls BOOLEAN NOT NULL DEFAULT 1"
            ))
        if "docker_verify_tls" not in host_columns:
            conn.execute(text(
                "ALTER TABLE managed_hosts ADD COLUMN docker_verify_tls BOOLEAN NOT NULL DEFAULT 1"
            ))
        if "docker_endpoint_id" not in host_columns:
            conn.execute(text(
                "ALTER TABLE managed_hosts ADD COLUMN docker_endpoint_id INTEGER"
            ))
        if "version_info" not in host_columns:
            conn.execute(text(
                "ALTER TABLE managed_hosts ADD COLUMN version_info VARCHAR(500)"
            ))
        docker_credential_columns = _columns(conn, "docker_credentials")
        if "api_key_encrypted" not in docker_credential_columns:
            conn.execute(text(
                "ALTER TABLE docker_credentials ADD COLUMN api_key_encrypted TEXT"
            ))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS host_access_grants (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                host_id INTEGER NOT NULL,
                subject_type VARCHAR(20) NOT NULL,
                subject_id INTEGER NOT NULL,
                can_connect BOOLEAN NOT NULL DEFAULT 1,
                can_execute BOOLEAN NOT NULL DEFAULT 0,
                can_manage_docker BOOLEAN NOT NULL DEFAULT 0,
                is_active BOOLEAN NOT NULL DEFAULT 1,
                expires_at TIMESTAMP,
                created_by_user_id INTEGER,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (host_id) REFERENCES managed_hosts(id) ON DELETE CASCADE,
                FOREIGN KEY (created_by_user_id) REFERENCES users(id),
                CONSTRAINT uq_host_access_subject UNIQUE (host_id, subject_type, subject_id)
            )
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS host_audit_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                host_id INTEGER NOT NULL,
                actor_type VARCHAR(20) NOT NULL,
                actor_id INTEGER NOT NULL,
                actor_name VARCHAR(200) NOT NULL,
                action VARCHAR(50) NOT NULL,
                target VARCHAR(255),
                command TEXT,
                status VARCHAR(20) NOT NULL,
                exit_code INTEGER,
                stdout TEXT,
                stderr TEXT,
                client_ip VARCHAR(100),
                duration_ms INTEGER,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (host_id) REFERENCES managed_hosts(id) ON DELETE CASCADE
            )
        """))
        conn.execute(text(
            "CREATE INDEX IF NOT EXISTS ix_host_access_subject "
            "ON host_access_grants(subject_type, subject_id)"
        ))
        conn.execute(text(
            "CREATE INDEX IF NOT EXISTS ix_host_audit_created "
            "ON host_audit_logs(created_at)"
        ))
        conn.commit()


if __name__ == "__main__":
    upgrade()
