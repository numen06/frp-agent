import base64
import threading
from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi import Depends, FastAPI, HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import auth
from app.database import Base, get_db
from app.models.user import User
from app.routers import login, frpc_config
from app.services.login_guard import LoginGuard


@pytest.fixture
def setup(monkeypatch):
    now = [1000.0]
    guard = LoginGuard(clock=lambda: now[0])
    monkeypatch.setattr(auth, 'login_guard', guard)
    monkeypatch.setattr(login, 'login_guard', guard)
    monkeypatch.setattr('app.services.login_guard.secrets.choice', lambda _: '7')
    engine = create_engine('sqlite://', connect_args={'check_same_thread': False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()
    db.add(User(username='operator', password_hash=auth.get_password_hash('correct-password'), role='admin', is_active=True))
    db.commit()
    app = FastAPI()
    app.include_router(login.router)
    app.include_router(frpc_config.router)
    app.dependency_overrides[get_db] = lambda: db

    @app.get('/private')
    def private(user=Depends(auth.get_current_user)):
        return {'username': user.username}

    yield TestClient(app), guard, now, db
    db.close()
    engine.dispose()


def payload(client, password='correct-password', captcha='77777'):
    result = client.get('/api/auth/captcha')
    assert result.status_code == 200
    assert result.headers['cache-control'] == 'no-store'
    return dict(username='operator', password=password, captcha=captcha,
                challenge_id=result.json()['challenge_id'])


def test_login_success_and_single_use_challenge(setup):
    client, _, now, _ = setup
    data = payload(client)
    assert client.post('/api/auth/login', json=data).json()['username'] == 'operator'
    replay = client.post('/api/auth/login', json=data)
    assert replay.status_code == 400
    assert replay.headers['retry-after'] == '2'


def test_captcha_wrong_expired_and_bound_to_address(setup):
    client, guard, now, _ = setup
    data = payload(client, captcha='12345')
    assert client.post('/api/auth/login', json=data).status_code == 400
    now[0] += 3
    data = payload(client)
    now[0] += 121
    assert client.post('/api/auth/login', json=data).status_code == 400
    c = guard.challenge('192.0.2.1')
    assert not guard.verify_challenge('192.0.2.2', c['challenge_id'], '77777')
    assert not guard.verify_challenge('192.0.2.1', c['challenge_id'], '77777')


def test_missing_captcha_rejected_before_password_check(setup, monkeypatch):
    client, _, _, _ = setup
    monkeypatch.setattr(auth, 'authenticate_user', lambda *args: pytest.fail('Password must not be checked'))
    assert client.post('/api/auth/login', json={'username': 'operator', 'password': 'anything'}).status_code == 422
    assert client.post('/api/auth/login', json=payload(client, captcha='00000')).status_code == 400


def test_backoff_shared_with_basic_auth_and_success_resets_account(setup):
    client, _, now, _ = setup
    first = client.post('/api/auth/login', json=payload(client, password='wrong'))
    assert first.status_code == 401
    assert first.headers['retry-after'] == '2'
    assert client.get('/private', auth=('operator', 'correct-password')).status_code == 429
    now[0] += 2
    second = client.get('/private', auth=('operator', 'wrong'))
    assert second.status_code == 401 and second.headers['retry-after'] == '4'
    now[0] += 4
    assert client.post('/api/auth/login', json=payload(client)).status_code == 200
    again = client.get('/private', auth=('operator', 'wrong'))
    assert again.headers['retry-after'] == '2'


def test_unknown_and_disabled_users_have_same_error(setup):
    client, _, now, db = setup
    unknown = client.get('/private', auth=('nobody', 'wrong'))
    user = db.query(User).filter_by(username='operator').one()
    user.is_active = False
    db.commit()
    disabled = client.get('/private', auth=('operator', 'correct-password'))
    assert unknown.status_code == disabled.status_code == 401
    assert unknown.json() == disabled.json()


def test_proxy_header_cannot_reset_backoff(setup):
    client, _, _, _ = setup
    client.get('/private', auth=('operator', 'wrong'))
    response = client.get('/private', auth=('operator', 'wrong'), headers={'X-Forwarded-For': '192.0.2.99'})
    assert response.status_code == 429


def test_legacy_routes_share_backoff_and_do_not_restore_default_password(setup, monkeypatch):
    client, _, now, _ = setup
    settings = auth.get_settings()
    monkeypatch.setattr(settings, 'auth_username', 'operator')
    monkeypatch.setattr(settings, 'auth_password', 'old-default')
    response = client.get('/api/frpc/get-my-token', auth=('operator', 'old-default'))
    assert response.status_code == 401
    token = base64.b64encode(b'operator:correct-password').decode()
    assert client.get('/api/frpc/config/direct/demo/office/frpc.ini', params={'token': token}).status_code == 429
    now[0] += 2
    assert client.get('/api/frpc/get-my-token', auth=('operator', 'correct-password')).status_code == 200
    # Valid legacy token reaches resource lookup instead of being blocked.
    assert client.get('/api/frpc/config/direct/demo/office/frpc.ini', params={'token': token}).status_code == 404


def test_capacity_rejects_without_evicting_live_challenges(setup):
    _, guard, _, _ = setup
    guard.capacity = 2
    first = guard.challenge('one')
    guard.challenge('two')
    with pytest.raises(HTTPException) as error:
        guard.challenge('three')
    assert error.value.status_code == 503
    assert guard.verify_challenge('one', first['challenge_id'], '77777')


def test_challenge_does_not_embed_answer_and_issuance_is_bounded(setup):
    _, guard, now, _ = setup
    challenge = guard.challenge('ip')
    svg = base64.b64decode(challenge['image'].split(',')[1]).decode()
    assert '<text' not in svg and '77777' not in svg
    assert challenge['expires_in'] == 120
    for _ in range(29):
        guard.challenge('ip')
    with pytest.raises(HTTPException) as error:
        guard.challenge('ip')
    assert error.value.status_code == 429
    now[0] += 61
    assert guard.challenge('ip')


def test_backoff_caps_and_expires():
    now = [0]
    guard = LoginGuard(clock=lambda: now[0])
    for expected in [2, 4, 8, 16, 32, 64, 128, 256, 300, 300]:
        with guard.attempt('ip', 'user') as states:
            assert guard.failure(states) == expected
        now[0] += expected
    now[0] += 901
    with guard.attempt('ip', 'user') as states:
        assert guard.failure(states) == 2


def test_rotating_usernames_hits_ip_backoff():
    guard = LoginGuard()
    for i in range(10):
        with guard.attempt('ip', str(i)) as states:
            guard.failure(states)
    with pytest.raises(HTTPException) as error:
        with guard.attempt('ip', 'another'):
            pytest.fail('IP backoff bypassed')
    assert error.value.status_code == 429


def test_parallel_attempt_cannot_bypass_failure():
    guard = LoginGuard()
    started = threading.Event()
    release = threading.Event()

    def first():
        with guard.attempt('ip', 'user') as states:
            started.set()
            assert release.wait(5)
            guard.failure(states)

    def second():
        assert started.wait(5)
        release.set()
        with pytest.raises(HTTPException) as error:
            with guard.attempt('ip', 'user'):
                pytest.fail('Parallel attempt bypassed backoff')
        assert error.value.status_code == 429

    with ThreadPoolExecutor(max_workers=2) as pool:
        a, b = pool.submit(first), pool.submit(second)
        a.result()
        b.result()
