"""Capture the built UI with isolated demo responses; never connects to a backend.

Install playwright==1.58.0 and its Chromium, then run with Vite preview on port 4173.
Screenshots are real 1920x1080 viewport captures (no resizing or compositing).
"""
import base64
from pathlib import Path
from urllib.parse import urlparse, parse_qs

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / 'docs' / 'screenshots'
BASE = 'http://127.0.0.1:4173'
VERSION = (ROOT / 'backend' / 'VERSION').read_text().strip()
DATE = '2026-10-17T09:30:00+08:00'

SERVERS = [dict(id=i, name=name, server_addr=f'frps-{i}.example.com', server_port=7000,
                api_base_url=f'https://frps-{i}.example.com/api', auth_username='operator',
                is_active=True, last_test_status='online', server_version='0.61.1',
                last_test_time=DATE, created_at=DATE)
           for i, name in enumerate(['华东 · 生产节点', '华北 · 业务节点', '研发 · 测试节点'], 1)]
PROXIES = [dict(id=i, frps_server_id=1, name=f'{group}_{service}', group_name=group,
                proxy_type='tcp', local_ip=f'10.20.0.{10+i}', local_port=port,
                remote_port=6000+i, status='offline' if i == 6 else 'online',
                client_version='0.61.1', created_at=DATE)
           for i, (group, service, port) in enumerate([
               ('office', 'ssh', 22), ('office', 'rdp', 3389), ('office', 'web', 8080),
               ('production', 'ssh', 22), ('production', 'mysql', 3306),
               ('staging', 'redis', 6379), ('staging', 'web', 8080), ('staging', 'ssh', 22)], 1)]
GROUPS = [dict(group_name=name, total_count=count, online_count=online,
               offline_count=count-online) for name, count, online in
          [('office', 3, 3), ('production', 2, 2), ('staging', 3, 2)]]
HOSTS = [dict(id=i, name=name, host_type=kind, address=f'{kind}-{i}.example.com', port=port,
              credential_name='演示凭据', credential_username=user, can_manage=True,
              permissions=['connect', 'execute', 'docker'], is_active=True,
              last_status='online', last_message='连接正常', tags=tag,
              version_info=version, host_key_fingerprint='SHA256:DEMO-FINGERPRINT',
              docker_use_tls=True, docker_endpoint_id=1)
         for i, (name, kind, port, user, tag, version) in enumerate([
             ('production-linux', 'ssh', 22, 'deploy', '生产环境 / 应用服务', 'Ubuntu 24.04 LTS'),
             ('production-docker', 'docker', 9443, '', '生产环境 / 容器集群', 'Docker 27.5.1'),
             ('office-windows', 'rdp', 3389, 'Administrator', '办公环境 / 远程桌面', 'Windows Server 2022'),
             ('staging-linux', 'ssh', 22, 'deploy', '测试环境 / 持续交付', 'Debian 12'),
             ('staging-docker', 'docker', 9443, '', '测试环境 / 容器服务', 'Docker 27.5.1'),
             ('office-build', 'ssh', 22, 'builder', '研发环境 / 构建节点', 'Ubuntu 22.04 LTS')], 1)]
PACKAGES = [dict(id=i, version='0.61.1', platform=platform,
                 filename=f'frp_0.61.1_{platform}.{ext}', file_size=12582912+i*1048576,
                 source='github', is_active=True, downloaded_at=DATE,
                 sha256_checksum='a1b2c3d4'*8)
            for i, (platform, ext) in enumerate([
                ('linux_amd64', 'tar.gz'), ('linux_arm64', 'tar.gz'),
                ('windows_amd64', 'zip'), ('darwin_arm64', 'tar.gz')], 1)]
KEYS = [dict(id=1, description='演示部署密钥', key='demo-key-not-a-real-credential',
             key_preview='demo_••••••••', is_active=True, expires_at=None,
             created_at=DATE, last_used_at=DATE)]
SUBJECTS = [dict(id=i, name=name, subject_type='user', role=role, is_active=True,
                has_ssh_public_key=True) for i, name, role in
            [(1, 'demo-admin', 'admin'), (2, 'operator', 'user')]]
GRANTS = [dict(id=h['id'], host_id=h['id'], host_name=h['name'], subject_type='user',
               subject_id=2, subject_name='operator', can_connect=True,
               can_execute=h['host_type']=='ssh', can_manage_docker=h['host_type']=='docker',
               is_active=True, is_expired=False) for h in HOSTS]
AUDIT = [dict(id=i, created_at=DATE, actor_name='operator', host_name=host,
              action=action, command=command, target='', status='success', exit_code=None,
              client_ip='192.0.2.10') for i, host, action, command in [
                  (1, 'office-windows', 'rdp_desktop_connected', ''),
                  (2, 'office-windows', 'rdp_gateway_authorized', ''),
                  (3, 'production-docker', 'docker_list', ''),
                  (4, 'production-linux', 'execute_command', 'uptime'),
                  (5, 'staging-linux', 'connection_test', ''),
                  (6, 'production-linux', 'ssh_gateway_session', '')]]


def paginated(items):
    return dict(items=items, total=len(items), page=1, page_size=20)


RESPONSES = {
    '/api/servers': SERVERS,
    '/api/settings/user': dict(username='demo-admin', role='admin'),
    '/api/settings/check-password': dict(require_password_change=False),
    '/api/system/version': dict(success=True, version=VERSION),
    '/api/public/version': dict(success=True, version=VERSION),
    '/api/system/version/check-update': dict(success=True, current_version=VERSION,
                                           latest_version=VERSION, has_update=False),
    '/api/api-keys': KEYS,
    '/api/api-keys/1/full-key': dict(key='demo-key-not-a-real-credential'),
    '/api/proxies': paginated(PROXIES),
    '/api/groups': paginated(GROUPS),
    '/api/groups/list': dict(groups=[g['group_name'] for g in GROUPS]),
    '/api/proxies/dashboard-stats/summary': dict(total=dict(total=24, online=22, offline=2, portCount=24)),
    '/api/proxies/dashboard-stats/server-stats': dict(server_stats={
        1: dict(total=8, online=7, offline=1, portCount=8),
        2: dict(total=10, online=10, offline=0, portCount=10),
        3: dict(total=6, online=5, offline=1, portCount=6)}),
    '/api/managed-hosts/context': dict(is_admin=True, actor_type='user', actor_name='demo-admin'),
    '/api/managed-hosts': HOSTS,
    '/api/managed-hosts/gateway/info': dict(port=2222, running=True,
        docker_gateway=dict(port=23750, running=True),
        rdp_gateway=dict(port=13389, running=True, public_address='rdp.example.com:13389')),
    '/api/managed-hosts/access/subjects': SUBJECTS,
    '/api/managed-hosts/access/grants': GRANTS,
    '/api/managed-hosts/audit/logs': AUDIT,
    '/api/managed-hosts/2/docker/containers': dict(containers=[]),
    '/api/docker-credentials': [],
    '/api/ssh-credentials': [],
    '/api/packages': paginated(PACKAGES),
    '/api/packages/versions': dict(versions=['0.61.1'], latest_version='0.61.1', recent_versions=['0.61.1'], synced_at=DATE),
    '/api/packages/releases': [dict(tag_name='v0.61.1', version='0.61.1', name='v0.61.1', platforms=[p['platform'] for p in PACKAGES])],
    '/api/packages/platforms': dict(platforms=[p['platform'] for p in PACKAGES]),
    '/api/packages/script-templates': {},
}


def demo_response(url):
    """Serve bounded demo collections using the same paging contract as production."""
    query = parse_qs(url.query)
    path = url.path
    data = RESPONSES.get(path)
    if path.startswith('/api/servers/') and path.rsplit('/', 1)[-1].isdigit():
        data = next((row for row in SERVERS if row['id'] == int(path.rsplit('/', 1)[-1])), None)
    if path.startswith('/api/api-keys/') and path.rsplit('/', 1)[-1].isdigit():
        data = next((row for row in KEYS if row['id'] == int(path.rsplit('/', 1)[-1])), None)
    if path.startswith('/api/api-keys/') and path.endswith('/full-key'):
        data = dict(key='demo-key-not-a-real-credential')
    if path.startswith('/api/managed-hosts/audit/logs/'):
        data = next((row for row in AUDIT if row['id'] == int(path.rsplit('/', 1)[-1])), None)
    if path.endswith('/delete-preview') and path.startswith('/api/groups/'):
        name = path.split('/')[-2]
        rows = [row for row in PROXIES if row['group_name'] == name]
        return dict(group_name=name, frps_server_id=1, proxy_count=len(rows), port_count=len(rows))
    if data is None:
        return None
    collection = data if isinstance(data, list) else data.get('items') if isinstance(data, dict) else None
    if path == '/api/groups/list':
        collection = [row['group_name'] for row in GROUPS]
    if path.endswith('/docker/containers'):
        collection = data.get('containers', [])
    if collection is None:
        return data
    rows = list(collection)
    if query.get('subject_type'):
        rows = [row for row in rows if row.get('subject_type') == query['subject_type'][0]]
    if query.get('selected'):
        rows = [row for row in rows if f"{row.get('subject_type')}:{row.get('id')}" == query['selected'][0]]
    if query.get('host_id'):
        key = 'id' if path == '/api/managed-hosts' else 'host_id'
        rows = [row for row in rows if str(row.get(key)) == query['host_id'][0]]
    if query.get('search'):
        term = query['search'][0].lower()
        rows = [row for row in rows if term in str(row).lower()]
    if query.get('available_only') == ['true']:
        rows = [row for row in rows if row.get('is_active') and not row.get('is_expired')]
    if 'page' not in query and isinstance(data, list):
        return rows[:20]
    page = int(query.get('page', ['1'])[0]); size = int(query.get('page_size', ['20'])[0])
    result = dict(items=rows[(page-1)*size:page*size], total=len(rows), page=page, page_size=size)
    if path == '/api/groups/list':
        result['groups'] = result['items']
    if path.endswith('/docker/containers'):
        result['containers'] = result['items']
    return result


def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        context = browser.new_context(viewport=dict(width=1920, height=1080),
                                      device_scale_factor=1, locale='zh-CN',
                                      timezone_id='Asia/Shanghai', reduced_motion='reduce',
                                      service_workers='block')

        def intercept(route):
            url = urlparse(route.request.url)
            if url.path.startswith('/api/'):
                payload = demo_response(url)
                if payload is None or route.request.method != 'GET':
                    errors.append(f'Unmocked request: {route.request.method} {url.path}')
                    route.fulfill(status=501, json=dict(detail='Screenshot fixture missing'))
                else:
                    route.fulfill(json=payload)
            elif url.netloc != '127.0.0.1:4173':
                errors.append(f'Unexpected external request: {url.netloc}')
                route.abort()
            else:
                route.continue_()

        context.route('**/*', intercept)
        context.add_init_script("""localStorage.setItem('auth_token', btoa('demo-admin:demo-only'));
            localStorage.setItem('username', 'demo-admin');
            localStorage.setItem('currentServerId', '1');""")
        page = context.new_page()
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.on('console', lambda msg: errors.append(msg.text) if msg.type == 'error' else None)
        page.on('dialog', lambda dialog: (errors.append(dialog.message), dialog.dismiss()))
        routes = ['dashboard', 'servers', 'proxies', 'groups', 'hosts', 'packages', 'api-keys', 'converter']
        review = ROOT / 'data' / 'ui-review'
        review.mkdir(parents=True, exist_ok=True)

        def settle():
            page.wait_for_load_state('networkidle')
            page.evaluate('document.fonts.ready')
            assert page.locator('main').is_visible()
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), page.url
            if page.viewport_size['width'] < 768:
                for select in page.locator('.app-select-native:visible').all():
                    assert select.evaluate('(el) => parseFloat(getComputedStyle(el).fontSize) >= 16')
                    assert select.bounding_box()['height'] >= 44

        for route in routes:
            page.goto(f'{BASE}/{route}')
            settle()
            page.screenshot(path=str(OUTPUT / f'{route}.png'), animations='disabled')
            print(f'Captured {route}: 1920x1080')
            if route == 'hosts':
                for label, filename in [('访问授权', 'host-access'), ('访问审计', 'host-audit')]:
                    page.get_by_role('button', name=label, exact=True).click()
                    settle()
                    page.screenshot(path=str(OUTPUT / f'{filename}.png'), animations='disabled')

        # Responsive smoke check uses the same real pages and demo responses.
        for width in [320, 390, 768, 1280]:
            page.set_viewport_size(dict(width=width, height=844))
            for route in routes:
                page.goto(f'{BASE}/{route}')
                settle()
                if width == 390:
                    page.screenshot(path=str(review / f'mobile-{route}.png'), animations='disabled')
            if width == 390:
                page.get_by_role('button', name='打开导航菜单').click()
                page.get_by_role('navigation', name='主导航').get_by_role('link', name='主机资源').click()
                page.wait_for_url('**/hosts')
                settle()
                assert page.url.endswith('/hosts')
                assert not page.get_by_role('navigation', name='主导航').is_visible()
            print(f'Responsive check passed: {width}px, {len(routes)} routes')

        def check_dialog(name):
            dialog = page.locator('.app-dialog:visible').last
            dialog.wait_for()
            page.wait_for_load_state('networkidle')
            panel = dialog.locator('.app-dialog-panel').first
            for height in [844, 420]:
                page.set_viewport_size(dict(width=390, height=height))
                page.wait_for_function('Math.abs(parseFloat(getComputedStyle(document.documentElement).getPropertyValue("--app-viewport-height")) - innerHeight) < 2')
                rect = panel.bounding_box()
                assert rect and abs(rect['y']) < 2 and abs(rect['height'] - height) < 2, (name, rect)
                assert panel.evaluate('(el) => el.scrollWidth <= el.clientWidth'), name
                body = dialog.locator('.app-dialog-body').first
                assert body.bounding_box()['height'] > 60, f'{name}: body collapsed'
                body.evaluate('(el) => { el.scrollTop = el.scrollHeight }')
                for button in dialog.locator('.app-dialog-footer button:visible').all():
                    if button.is_enabled():
                        button.click(trial=True)
                close = dialog.get_by_role('button', name='关闭', exact=True).first
                close.click(trial=True)
            page.screenshot(path=str(review / f'dialog-{name}-keyboard.png'), animations='disabled')
            page.set_viewport_size(dict(width=390, height=844))
            page.wait_for_function('parseFloat(getComputedStyle(document.documentElement).getPropertyValue("--app-viewport-height")) > 800')
            page.screenshot(path=str(review / f'dialog-{name}.png'), animations='disabled')
            close.click()
            assert page.locator('.app-dialog:visible').count() == 0, name
            assert page.evaluate('document.body.style.overflow') != 'hidden', name
            print(f'Dialog touch/scroll/close check passed: {name}')

        page.set_viewport_size(dict(width=390, height=844))
        for route, label in [('servers', '添加服务器'), ('api-keys', '创建密钥'),
                             ('groups', '新增分组'), ('groups', '导入/整理'), ('groups', '查看代理'),
                             ('packages', '手动上传'), ('packages', 'GitHub 同步'),
                             ('packages', '脚本生成'), ('hosts', '添加主机'),
                             ('hosts', 'AI / curl 添加提示词'), ('hosts', '连接凭证'),
                             ('hosts', '命令终端'), ('hosts', '容器管理'), ('proxies', '客户端升级')]:
            page.goto(f'{BASE}/{route}')
            settle()
            page.get_by_role('button', name=label, exact=True).first.click()
            check_dialog(label.replace(' / ', '-'))

        for host_type in ['Docker 主机', 'RDP 主机']:
            page.goto(f'{BASE}/hosts')
            settle()
            page.get_by_role('button', name='添加主机', exact=True).click()
            page.get_by_role('button', name=host_type, exact=True).click()
            check_dialog(host_type)

        for label in ['生成配置', '客户端升级', '重命名']:
            page.goto(f'{BASE}/groups')
            settle()
            page.get_by_role('button', name='更多操作', exact=True).first.click()
            page.get_by_role('button', name=label, exact=True).click()
            check_dialog(f'分组-{label}')

        for label in ['添加代理', '导入配置']:
            page.goto(f'{BASE}/proxies')
            settle()
            page.get_by_role('button', name='添加菜单', exact=True).click()
            page.get_by_role('link', name=label, exact=True).click()
            check_dialog(label)

        page.goto(f'{BASE}/dashboard')
        settle()
        page.get_by_role('button', name='版本与更新').click()
        check_dialog('版本与更新')

        # Exercise the actual login form, including a failed response and retry.
        login_context = browser.new_context(viewport=dict(width=1920, height=1080), device_scale_factor=1,
                                            locale='zh-CN', reduced_motion='reduce', service_workers='block')
        login_attempts = []
        captcha_requests = []
        demo_svg = '<svg xmlns="http://www.w3.org/2000/svg" width="180" height="56"><rect width="180" height="56" fill="#eff6ff"/><text x="15" y="39" font-size="34" letter-spacing="5" fill="#1e40af">24680</text></svg>'

        def login_intercept(route):
            path = urlparse(route.request.url).path
            if path == '/api/auth/captcha':
                captcha_requests.append(path)
                route.fulfill(json=dict(challenge_id=f'demo-{len(captcha_requests)}', expires_in=120,
                    image='data:image/svg+xml;base64,' + base64.b64encode(demo_svg.encode()).decode()))
            elif path == '/api/auth/login':
                data = route.request.post_data_json
                assert data['captcha'] == '24680' and data['challenge_id'].startswith('demo-')
                login_attempts.append(data)
                if len(login_attempts) == 1:
                    route.fulfill(status=401, headers={'Retry-After': '2'}, json=dict(detail='用户名或密码错误'))
                else:
                    route.fulfill(json=dict(success=True, username='demo-admin', role='admin'))
            else:
                intercept(route)

        login_context.route('**/*', login_intercept)
        login_page = login_context.new_page()
        login_page.on('pageerror', lambda error: errors.append(str(error)))
        login_page.goto(f'{BASE}/login')
        login_page.get_by_role('img', name='登录验证码，点击可更换').wait_for()
        login_page.screenshot(path=str(OUTPUT / 'login.png'), animations='disabled')
        login_page.set_viewport_size(dict(width=390, height=844))
        login_page.screenshot(path=str(review / 'mobile-login.png'), animations='disabled')
        login_page.get_by_label('用户名', exact=True).fill('demo-admin')
        login_page.get_by_label('密码', exact=True).fill('wrong-password')
        login_page.get_by_label('验证码', exact=True).fill('24680')
        login_page.get_by_role('button', name='登录', exact=True).click()
        login_page.get_by_text('用户名或密码错误', exact=True).wait_for()
        assert login_page.locator('button[type=submit]').is_disabled()
        assert login_page.evaluate('localStorage.getItem("auth_token")') is None
        login_page.wait_for_function('!document.querySelector("button[type=submit]").disabled')
        assert len(captcha_requests) == 2
        login_page.get_by_label('密码', exact=True).fill('correct-password')
        login_page.get_by_label('验证码', exact=True).fill('24680')
        login_page.get_by_label('验证码', exact=True).press('Enter')
        login_page.wait_for_url('**/dashboard')
        assert len(login_attempts) == 2
        print('Login form: CAPTCHA refresh, failure countdown, single submit and success passed')
        login_context.close()
        browser.close()
    assert not errors, '\n'.join(errors)
    print('No runtime errors, external requests, or page-level horizontal overflow.')


if __name__ == '__main__':
    main()
