"""Inventory and groups; permissions stay on individual connection profiles."""
from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.auth import get_current_user
from app.database import get_db
from app.models.host_machine import HostMachine
from app.models.managed_host import ManagedHost
from app.models.frps_server import FrpsServer
from app.models.group import Group
from app.models.proxy import Proxy
from app.models.user import User
from app.pagination import PageParams, paginate, search_query
from app.services.host_access_service import accessible_host_ids, is_admin, require_admin

router = APIRouter(prefix='/api/host-machines', tags=['主机与连接服务'])


class MachineWrite(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: str | None = Field(None, max_length=2000)
    group_key: str | None = Field(None, max_length=100)

    @field_validator('name')
    @classmethod
    def name_required(cls, value):
        value = value.strip()
        if not value:
            raise ValueError('主机名称不能为空')
        return value


def visible_services(db, user):
    query = db.query(ManagedHost)
    if not is_admin(user):
        query = query.filter(ManagedHost.id.in_(accessible_host_ids(db, user)), ManagedHost.is_active.is_(True))
    return query


def machine_record(db, user, mid):
    machine = db.get(HostMachine, mid)
    if not machine or (not is_admin(user) and not visible_services(db, user).filter(ManagedHost.machine_id == mid).first()):
        raise HTTPException(404, '主机不存在或无权查看')
    return machine


def record(machine, server_name=None, count=0):
    return dict(id=machine.id, name=machine.name, description=machine.description,
                group_key=f'{machine.frps_server_id}:{machine.group_name}' if machine.group_name and machine.frps_server_id else None,
                group_name=machine.group_name, server_name=server_name, service_count=count)


def set_group(db, machine, key):
    if not key:
        machine.frps_server_id = machine.group_name = None
        return
    try:
        sid, name = key.split(':', 1)
        sid = int(sid)
    except (ValueError, AttributeError):
        raise HTTPException(400, '请选择已有分组')
    exists = (db.query(Group.id).filter_by(frps_server_id=sid, name=name).first()
              or db.query(Proxy.id).filter_by(frps_server_id=sid, group_name=name).first()
              or db.query(HostMachine.id).filter_by(frps_server_id=sid, group_name=name).first())
    if not exists or not db.get(FrpsServer, sid) or len(name) > 50:
        raise HTTPException(400, '分组不存在，请刷新后重新选择')
    machine.frps_server_id, machine.group_name = sid, name


@router.get('/groups')
def groups(paging: PageParams = Depends(), db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    require_admin(user)
    names = db.query(Group.frps_server_id.label('sid'), Group.name.label('name')).union(
        db.query(Proxy.frps_server_id, Proxy.group_name).filter(Proxy.group_name.isnot(None), Proxy.group_name != ''),
        db.query(HostMachine.frps_server_id, HostMachine.group_name).filter(HostMachine.group_name.isnot(None))).subquery()
    query = db.query(names.c.sid, names.c.name, FrpsServer.name.label('server')).join(FrpsServer, FrpsServer.id == names.c.sid)
    query = search_query(query, paging.search, names.c.name, FrpsServer.name).order_by(FrpsServer.name, names.c.name)
    return paginate(query, paging, lambda row: dict(id=f'{row.sid}:{row.name}', name=f'{row.server} / {row.name}'))


@router.get('')
def machines(response: Response, paging: PageParams = Depends(), group_key: str | None = None,
             db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    response.headers['Cache-Control'] = 'no-store'
    counts = visible_services(db, user).with_entities(ManagedHost.machine_id.label('mid'), func.count(ManagedHost.id).label('total')).group_by(ManagedHost.machine_id).subquery()
    query = db.query(HostMachine, FrpsServer.name, counts.c.total).outerjoin(FrpsServer, FrpsServer.id == HostMachine.frps_server_id).outerjoin(counts, counts.c.mid == HostMachine.id)
    if not is_admin(user):
        query = query.filter(counts.c.total > 0)
    if group_key:
        if group_key == 'ungrouped':
            query = query.filter(HostMachine.group_name.is_(None))
        else:
            try:
                sid, name = group_key.split(':', 1)
                query = query.filter(HostMachine.frps_server_id == int(sid), HostMachine.group_name == name)
            except ValueError:
                raise HTTPException(400, '分组筛选无效')
    query = search_query(query, paging.search, HostMachine.name, HostMachine.group_name).order_by(HostMachine.id.desc())
    return paginate(query, paging, lambda row: record(row[0], row[1], row[2] or 0))


@router.get('/{mid}')
def detail(mid: int, response: Response, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    response.headers['Cache-Control'] = 'no-store'
    machine = machine_record(db, user, mid)
    server = db.get(FrpsServer, machine.frps_server_id) if machine.frps_server_id else None
    return record(machine, server.name if server else None, visible_services(db, user).filter(ManagedHost.machine_id == mid).count())


@router.post('', status_code=201)
def create(body: MachineWrite, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    require_admin(user)
    machine = HostMachine(name=body.name, description=body.description)
    set_group(db, machine, body.group_key)
    db.add(machine); db.commit(); db.refresh(machine)
    return record(machine)


@router.put('/{mid}')
def update(mid: int, body: MachineWrite, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    require_admin(user)
    machine = machine_record(db, user, mid)
    set_group(db, machine, body.group_key)
    machine.name, machine.description = body.name, body.description
    db.commit()
    return record(machine)


@router.delete('/{mid}', status_code=204)
def remove(mid: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    require_admin(user)
    machine = machine_record(db, user, mid)
    if db.query(ManagedHost.id).filter_by(machine_id=mid).first():
        raise HTTPException(409, '主机仍有连接服务，请先移动或删除服务；授权和审计不会随主机分组扩大')
    db.delete(machine); db.commit()
