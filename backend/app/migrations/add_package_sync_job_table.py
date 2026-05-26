"""GitHub 安装包同步任务表迁移"""
from sqlalchemy import text
from app.database import engine


def upgrade():
    with engine.connect() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS package_sync_jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id VARCHAR(36) NOT NULL UNIQUE,
                status VARCHAR(20) NOT NULL DEFAULT 'queued',
                version VARCHAR(50) NOT NULL,
                platforms TEXT,
                download_source VARCHAR(20) NOT NULL DEFAULT 'origin',
                total INTEGER NOT NULL DEFAULT 0,
                completed INTEGER NOT NULL DEFAULT 0,
                results TEXT,
                error TEXT,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                started_at TIMESTAMP,
                finished_at TIMESTAMP
            )
        """))
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS ix_package_sync_jobs_job_id
            ON package_sync_jobs(job_id)
        """))
        conn.commit()
