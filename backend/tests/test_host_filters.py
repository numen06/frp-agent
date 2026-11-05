"""Host filters run before pagination and preserve existing access boundaries."""
from datetime import datetime, timedelta
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.auth import get_current_user
from app.database import Base, get_db
from app.models.user import User
from app.models.managed_host import ManagedHost, HostAccessGrant
from app.webssh import app


@pytest.fixture
def env():
    engine=create_engine('sqlite://',connect_args={'check_same_thread':False},poolclass=StaticPool)
    Base.metadata.create_all(engine); factory=sessionmaker(bind=engine)
    actor=[User(id=0,username='admin',role='admin',password_hash='')]
    with factory() as db:
        db.add(User(id=2,username='member',role='user',password_hash='x',is_active=True))
        for i in range(1,37):
            db.add(ManagedHost(id=i,name=f'host-{i}',address=f'192.0.2.{i}',port=22,
                host_type=['ssh','rdp','docker'][i%3],last_status=['online','offline','error','unknown'][i%4],
                is_active=i%5!=0,tags='production' if i%2 else 'test'))
        db.flush()
        for i in [1,2,5,7,8]:
            db.add(HostAccessGrant(host_id=i,subject_type='user',subject_id=2,can_connect=True,
                expires_at=datetime.utcnow()-timedelta(hours=1) if i==8 else None))
        db.commit()
    def session():
        with factory() as db: yield db
    app.dependency_overrides[get_db]=session
    app.dependency_overrides[get_current_user]=lambda:actor[0]
    with TestClient(app) as client: yield client,actor
    app.dependency_overrides.clear();engine.dispose()


def test_combined_filters_count_all_pages(env):
    client,_=env
    ids=[]
    for page in [1,2,3]:
        r=client.get('/api/managed-hosts',params=dict(page=page,page_size=2,host_type='ssh',host_status='abnormal'))
        assert r.status_code==200
        data=r.json()
        assert data['total']==5
        assert len(data['items'])==(1 if page==3 else 2)
        ids += [h['id'] for h in data['items']]
        assert all(h['host_type']=='ssh' and h['is_active'] and h['last_status'] in ['offline','error'] for h in data['items'])
        assert all('password' not in h and 'private_key' not in h for h in data['items'])
    assert ids==[33,21,18,9,6]


@pytest.mark.parametrize('status',['online','abnormal','unknown','disabled'])
def test_status_and_search(env,status):
    client,_=env
    tag='test' if status=='online' else 'production'
    data=client.get('/api/managed-hosts',params=dict(page=1,page_size=100,host_status=status,search=tag)).json()
    assert data['items']
    for host in data['items']:
        assert host['tags']==tag
        if status=='disabled': assert not host['is_active']
        else:
            assert host['is_active']
            assert (host['last_status']=='online' if status=='online' else host['last_status'] in ['offline','error'] if status=='abnormal' else host['last_status']=='unknown')


def test_member_cannot_expand_authorization_with_filters(env):
    client,actor=env;actor[0]=User(id=2,username='member',role='user',password_hash='x',is_active=True)
    data=client.get('/api/managed-hosts',params=dict(page=1,page_size=100)).json()
    assert {h['id'] for h in data['items']}=={1,2,7}
    assert client.get('/api/managed-hosts',params=dict(page=1,host_status='disabled')).json()['total']==0
    assert client.get('/api/managed-hosts',params=dict(page=1,host_id=8)).json()['total']==0
    assert client.get('/api/managed-hosts',params=dict(page=1,host_type='ssh')).json()['total']==0


def test_invalid_filters_are_rejected_and_read_worker_has_no_write_route(env):
    client,_=env
    assert client.get('/api/managed-hosts?host_type=invalid').status_code==422
    assert client.get('/api/managed-hosts?host_status=invalid').status_code==422
    assert client.post('/api/managed-hosts',json={}).status_code==405
