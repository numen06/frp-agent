"""Exercise shared UI and host workflows against isolated fake APIs only."""
from copy import deepcopy
from pathlib import Path
import sys
from urllib.parse import urlparse, parse_qs
from playwright.sync_api import sync_playwright, expect
import capture_screenshots as demo
from check_runtime import fixture as runtime_fixture


def main():
    output = Path(__file__).resolve().parents[2] / '.codex-remote-attachments/ui-acceptance'
    output.mkdir(parents=True, exist_ok=True)
    hosts = deepcopy(demo.HOSTS)
    state = dict(admin=True, fail_save=False, fail_delete=False, writes=[], fail_load=False)
    errors = []

    def intercept(route):
        u = urlparse(route.request.url); method = route.request.method
        if u.netloc != '127.0.0.1:4173':
            errors.append('Unexpected external request'); route.abort(); return
        if not u.path.startswith('/api/'):
            route.continue_(); return
        if u.path == '/api/managed-hosts/context':
            route.fulfill(json=dict(is_admin=state['admin'], actor_type='user', actor_name='demo-admin')); return
        if u.path == '/api/settings/user':
            route.fulfill(json=dict(username='demo-admin', role='admin' if state['admin'] else 'user')); return
        if u.path == '/api/system/overview':
            route.fulfill(json=runtime_fixture()); return
        if u.path == '/api/managed-hosts' and method == 'GET':
            if state['fail_load']:
                route.fulfill(status=503, json=dict(detail='主机读取失败，请重试')); return
            query = parse_qs(u.query)
            rows = [h for h in hosts if not query.get('host_id') or str(h['id']) == query['host_id'][0]]
            if query.get('search'): rows = [h for h in rows if query['search'][0] in h['name']]
            route.fulfill(json=demo.paginated(rows)); return
        if method != 'GET':
            state['writes'].append((method, u.path, route.request.post_data_json if route.request.post_data else None))
            if method in ['PUT', 'POST'] and u.path.startswith('/api/managed-hosts'):
                if state['fail_save']:
                    route.fulfill(status=422, json=dict(detail='名称已存在，请更换名称')); return
                data = route.request.post_data_json
                if u.path == '/api/managed-hosts/rdp/fingerprint':
                    route.fulfill(json=dict(fingerprint='SHA256:NEW-RDP-TEST')); return
                if u.path == '/api/managed-hosts':
                    row = dict(deepcopy(hosts[0]), **data); row['id'] = 99; hosts.append(row)
                else:
                    row = next(h for h in hosts if str(h['id']) == u.path.rsplit('/', 1)[1]); row.update(data)
                route.fulfill(json=row); return
            if method == 'DELETE':
                if state['fail_delete']:
                    route.fulfill(status=409, json=dict(detail='演示删除失败，请重试')); return
                hosts[:] = [h for h in hosts if str(h['id']) != u.path.rsplit('/', 1)[1]]
                route.fulfill(json=dict(success=True)); return
            errors.append(f'Unexpected mutation: {method} {u.path}'); route.abort(); return
        data = demo.demo_response(u)
        if data is None: errors.append('Missing fixture: '+u.path)
        route.fulfill(json=data or {})

    with sync_playwright() as p:
        browser = p.chromium.launch()
        context = browser.new_context(viewport=dict(width=1920, height=1080), locale='zh-CN', reduced_motion='reduce', service_workers='block')
        context.route('**/*', intercept)
        context.add_init_script("localStorage.setItem('auth_token',btoa('demo-admin:demo-only'));localStorage.setItem('username','demo-admin');localStorage.setItem('currentServerId','1')")
        page = context.new_page()
        page.on('pageerror', lambda e: errors.append(str(e)))
        page.on('dialog', lambda d: (errors.append('Unexpected native dialog: '+d.type), d.dismiss()))

        def settle():
            page.wait_for_load_state('networkidle')
            if not page.evaluate('document.documentElement.scrollWidth <= innerWidth'):
                page.screenshot(path=str(output/'overflow.png'), full_page=True)
                print(page.evaluate("[...document.querySelectorAll('main *')].filter(el => el.getClientRects().length && el.getBoundingClientRect().right > innerWidth).map(el => ({tag:el.tagName,cls:el.className,right:el.getBoundingClientRect().right,text:el.textContent.slice(0,60)})).slice(-12)"), flush=True)
                raise AssertionError(page.url)

        routes = ['dashboard', 'operations', 'proxies', 'groups', 'servers', 'hosts', 'packages', 'api-keys', 'converter', 'hosts/new', 'hosts/1/edit', 'hosts/2/edit', 'hosts/3/edit']
        for width in ([] if '--workflows-only' in sys.argv else [320, 390, 768, 1280, 1920]):
            page.set_viewport_size(dict(width=width, height=844 if width < 768 else 1080))
            for path in routes:
                page.goto(demo.BASE+'/'+path); settle()
                expect(page.locator('main h1')).to_have_count(1)
                if '/edit' in path or path == 'hosts/new':
                    expect(page.locator('#host-editor-form')).to_be_visible()
                    expect(page.get_by_role('dialog')).to_have_count(0)
                if width in [390, 1920] and path in ['hosts', 'hosts/1/edit', 'operations', 'proxies']:
                    page.screenshot(path=str(output/(path.replace('/', '-')+f'-{width}.png')), full_page=True)
            print(f'Shared layouts, one heading, standalone editor, no overflow: {width}px / {len(routes)} routes', flush=True)

        page.set_viewport_size(dict(width=390, height=844))
        page.goto(demo.BASE+'/hosts?search=production&page=1'); settle()
        card = page.locator('article').filter(has=page.get_by_role('heading', name='production-linux', exact=True))
        card.get_by_role('button', name='主机操作', exact=True).click()
        page.get_by_role('menuitem', name='编辑连接', exact=True).click(); settle()
        expect(page).to_have_url(demo.BASE+'/hosts/1/edit?page=1&page_size=20&search=production')
        name = page.get_by_label('连接名称', exact=True)
        expect(name).to_have_value('production-linux')
        name.fill('edited-linux')
        page.get_by_label('选择所属主机',exact=True).click()
        page.get_by_role('option',name='production-linux (#1)',exact=True).click()
        before = len(state['writes'])
        page.get_by_role('link', name='返回所属主机', exact=False).click()
        dialog = page.get_by_role('alertdialog', name='放弃未保存的修改')
        expect(dialog).to_be_visible()
        dialog.get_by_role('button', name='取消', exact=True).click()
        expect(name).to_have_value('edited-linux')
        assert len(state['writes']) == before
        state['fail_save'] = True
        page.get_by_role('button', name='保存连接服务', exact=True).first.click(); settle()
        expect(page.get_by_role('alert')).to_contain_text('名称已存在')
        expect(name).to_have_value('edited-linux')
        state['fail_save'] = False
        page.get_by_role('button', name='保存连接服务', exact=True).first.click(); settle()
        expect(page).to_have_url(demo.BASE+'/hosts?page=1&page_size=20&search=production')
        assert state['writes'][-1][0:2] == ('PUT', '/api/managed-hosts/1')
        assert state['writes'][-1][2]['credential_id'] == 1
        assert state['writes'][-1][2]['host_key_fingerprint'] == 'SHA256:DEMO-FINGERPRINT'
        print('Editor links, query restoration, unsaved cancel, save failure, update payload and success passed', flush=True)

        page.goto(demo.BASE+'/hosts/3/clone'); settle()
        expect(page.get_by_label('连接名称', exact=True)).to_have_value('office-windows 副本')
        expect(page.get_by_label('Windows RDP 证书 SHA256 指纹')).to_have_value('')
        page.get_by_label('选择所属主机',exact=True).click()
        page.get_by_role('option',name='office-windows (#3)',exact=True).click()
        page.get_by_label('连接地址', exact=True).fill('new-windows.example.com')
        page.get_by_role('button', name='获取指纹', exact=True).click(); settle()
        expect(page.get_by_label('Windows RDP 证书 SHA256 指纹')).to_have_value('SHA256:NEW-RDP-TEST')
        page.get_by_role('button', name='保存连接服务', exact=True).first.click(); settle()
        expect(page).to_have_url(demo.BASE+'/hosts')
        assert state['writes'][-1][0:2] == ('POST', '/api/managed-hosts')
        assert state['writes'][-1][2]['host_key_fingerprint'] == 'SHA256:NEW-RDP-TEST'

        card = page.locator('article').filter(has=page.get_by_role('heading', name='edited-linux', exact=True))
        card.get_by_role('button', name='主机操作', exact=True).click()
        page.get_by_role('menuitem', name='删除连接服务', exact=True).click()
        dialog = page.get_by_role('alertdialog', name='删除连接服务', exact=True)
        expect(dialog).to_contain_text('edited-linux')
        expect(dialog).to_contain_text('授权与审计记录')
        page.screenshot(path=str(output/'delete-confirm-mobile.png'))
        before = len(state['writes']); dialog.get_by_role('button', name='取消', exact=True).click()
        assert len(state['writes']) == before
        state['fail_delete'] = True
        card.get_by_role('button', name='主机操作', exact=True).click()
        page.get_by_role('menuitem', name='删除连接服务', exact=True).click()
        dialog.get_by_role('button', name='删除连接', exact=True).click(); settle()
        expect(card).to_be_visible(); expect(page.locator('[data-sonner-toast]').filter(has_text='演示删除失败')).to_contain_text('演示删除失败')
        state['fail_delete'] = False
        card.get_by_role('button', name='主机操作', exact=True).click()
        page.get_by_role('menuitem', name='删除连接服务', exact=True).click()
        dialog.get_by_role('button', name='删除连接', exact=True).click(); settle()
        expect(card).to_have_count(0)
        print('Clone and fingerprint, delete confirmation/cancel/failure/success passed', flush=True)

        page.goto(demo.BASE+'/hosts/999/edit'); settle()
        expect(page.get_by_role('alert')).to_contain_text('主机不存在')
        state['fail_load'] = True; page.goto(demo.BASE+'/hosts/2/edit'); settle()
        expect(page.get_by_role('alert')).to_contain_text('主机读取失败')
        state['fail_load'] = False; page.get_by_role('button', name='重试', exact=True).click(); settle()
        expect(page.locator('#host-editor-form')).to_be_visible()
        state['admin'] = False
        page.goto(demo.BASE+'/hosts/2/edit'); settle()
        expect(page).to_have_url(demo.BASE+'/hosts')
        expect(page.locator('#host-editor-form')).to_have_count(0)
        browser.close()
    assert not errors, errors
    print('UI acceptance passed; all writes used local fixtures, no production data changed.', flush=True)


if __name__ == '__main__':
    main()
