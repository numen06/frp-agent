"""Add inventory identity without changing connection IDs, grants or audits."""
from sqlalchemy import text
from app.database import engine
from app.models.host_machine import HostMachine


def upgrade():
    HostMachine.__table__.create(engine, checkfirst=True)
    with engine.begin() as conn:
        columns = {row[1] for row in conn.execute(text('PRAGMA table_info(managed_hosts)'))}
        if 'machine_id' not in columns:
            conn.execute(text('ALTER TABLE managed_hosts ADD COLUMN machine_id INTEGER REFERENCES host_machines(id)'))
        conn.execute(text('CREATE INDEX IF NOT EXISTS ix_managed_hosts_machine_id ON managed_hosts(machine_id)'))
        tables = {row[0] for row in conn.execute(text("SELECT name FROM sqlite_master WHERE type='table'"))}
        for host in conn.execute(text('SELECT id,name,description FROM managed_hosts WHERE machine_id IS NULL')).mappings().all():
            group = None
            if 'host_proxy_sources' in tables:
                group = conn.execute(text('SELECT p.frps_server_id,p.group_name FROM host_proxy_sources s JOIN proxies p ON p.id=s.proxy_id WHERE s.host_id=:id'), {'id': host['id']}).mappings().first()
            result = conn.execute(HostMachine.__table__.insert().values(
                name=host['name'], description=host['description'],
                frps_server_id=group['frps_server_id'] if group and group['group_name'] else None,
                group_name=group['group_name'] if group else None))
            conn.execute(text('UPDATE managed_hosts SET machine_id=:machine WHERE id=:id'), {'machine': result.inserted_primary_key[0], 'id': host['id']})
