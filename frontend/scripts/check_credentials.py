"""Credential UI regression using intercepted demo APIs; no production access."""
from copy import deepcopy
from urllib.parse import urlparse, parse_qs
from playwright.sync_api import sync_playwright, expect
import capture_screenshots as demo


def main():
    for rows, count, prefix in [(demo.SSH_CREDENTIALS, 45, 'ssh'), (demo.DOCKER_CREDENTIALS, 43, 'docker')]:
        original = deepcopy(rows[0])
        rows[:] = [dict(original, id=i, name=f'{prefix}-demo-{i:03}') for i in range(1, count+1)]
    errors, mutations, queries = [], [], []

    def intercept(route):
        url = urlparse(route.request.url)
        if url.netloc != '127.0.0.1:4173':
            errors.append('External request blocked'); route.abort(); return
        if not url.path.startswith('/api/'):
            route.continue_(); return
        path, method = url.path, route.request.method
        if method != 'GET':
            assert path.startswith(('/api/ssh-credentials', '/api/docker-credentials'))
            payload = route.request.post_data_json if route.request.post_data else {}
            mutations.append((method, path, payload))
            rows = demo.SSH_CREDENTIALS if path.startswith('/api/ssh-credentials') else demo.DOCKER_CREDENTIALS
            if method == 'DELETE':
                cid = int(path.rsplit('/', 1)[-1])
                if cid == 1:
                    route.fulfill(status=409, json=dict(detail='该凭据正被 2 台主机使用，请先调整主机配置')); return
                rows[:] = [row for row in rows if row['id'] != cid]
                route.fulfill(status=204); return
            row = next((r for r in rows if str(r['id']) == path.rsplit('/', 1)[-1]), None) if method == 'PUT' else None
            if row is None:
                row = dict(id=max(r['id'] for r in rows)+1, created_at=demo.DATE, updated_at=demo.DATE)
                rows.append(row)
            for key, value in payload.items():
                if key in ['password', 'private_key', 'passphrase', 'sudo_password', 'api_key', 'ca_cert']:
                    row['has_' + key] = bool(value)
                else:
                    row[key] = value
            route.fulfill(status=201 if method == 'POST' else 200, json=row); return
        queries.append((path, parse_qs(url.query)))
        data = demo.demo_response(url)
        if data is None:
            errors.append('Missing fixture: ' + path); route.fulfill(status=501, json={})
        else:
            route.fulfill(json=data)

    with sync_playwright() as p:
        browser = p.chromium.launch()
        context = browser.new_context(viewport=dict(width=1280, height=900), locale='zh-CN', service_workers='block')
        context.route('**/*', intercept)
        context.add_init_script("localStorage.setItem('auth_token', btoa('demo-admin:demo-only'));localStorage.setItem('username','demo-admin')")
        page = context.new_page(); page.on('pageerror', lambda e: errors.append(str(e)))

        def settle():
            page.wait_for_load_state('networkidle')
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')

        def open_panel(kind='ssh'):
            page.goto(demo.BASE + '/hosts'); settle()
            page.get_by_role('button', name='凭证管理', exact=True).click(); settle()
            if kind == 'docker':
                page.get_by_role('button', name='Docker / Portainer', exact=True).click(); settle()

        for width in [1280, 390]:
            page.set_viewport_size(dict(width=width, height=844))
            for kind in ['ssh', 'docker']:
                open_panel(kind)
                if width > 768:
                    expect(page.locator('main table:visible tbody tr')).to_have_count(20)
                page.get_by_role('button' if width < 768 else 'link', name='下一页', exact=True).last.click(); settle()
                prefix = f'/api/{kind}-credentials'
                assert any(path == prefix and query.get('page') == ['2'] and query.get('page_size') == ['20'] for path, query in queries)
                page.get_by_label('搜索凭证').fill(f'{kind}-demo-045' if kind == 'ssh' else 'docker-demo-043')
                page.get_by_role('button', name='搜索', exact=True).click(); settle()
                expect(page.get_by_role('button', name='编辑', exact=True)).to_have_count(1)
            print(f'Credential search and 20-row pagination: {width}px', flush=True)

        page.set_viewport_size(dict(width=390, height=844)); open_panel()
        page.get_by_role('button', name='编辑', exact=True).first.click()
        dialog = page.get_by_role('dialog', name='编辑凭证', exact=True)
        for field in dialog.locator('input[type=password], textarea').all():
            assert field.input_value() == ''
        dialog.get_by_label('凭证名称', exact=True).fill('renamed-demo')
        for height in [844, 420]:
            page.set_viewport_size(dict(width=390, height=height))
            page.wait_for_function('Math.abs(parseFloat(getComputedStyle(document.documentElement).getPropertyValue("--app-viewport-height")) - innerHeight) < 2')
            rect = dialog.locator('.app-dialog-panel').bounding_box()
            assert abs(rect['y']) < 2 and abs(rect['height'] - height) < 2
            dialog.get_by_role('button', name='保存凭证', exact=True).click(trial=True)
        dialog.get_by_role('button', name='保存凭证', exact=True).click(); settle()
        expect(dialog).not_to_be_visible()
        payload = mutations[-1][2]
        assert payload == dict(name='renamed-demo', username='deploy', auth_type='private_key')
        page.set_viewport_size(dict(width=390, height=844))
        page.get_by_role('button', name='编辑', exact=True).first.click()
        dialog.get_by_label('私钥口令', exact=True).fill('demo-new-passphrase')
        dialog.get_by_label('清除已保存的sudo 密码', exact=True).check()
        dialog.get_by_role('button', name='保存凭证', exact=True).click(); settle()
        assert mutations[-1][2]['passphrase'] == 'demo-new-passphrase' and mutations[-1][2]['sudo_password'] == ''

        # Cancellation is read-only; the server's in-use conflict remains visible.
        page.get_by_role('button', name='删除', exact=True).first.click()
        deletion = page.get_by_role('dialog', name='删除凭证', exact=True)
        deletion.get_by_role('button', name='取消', exact=True).click()
        assert not any(method == 'DELETE' for method, *_ in mutations)
        page.get_by_role('button', name='删除', exact=True).first.click()
        deletion.get_by_role('button', name='确认删除', exact=True).click(); settle()
        expect(deletion.get_by_role('alert')).to_contain_text('2 台主机')
        deletion.get_by_role('button', name='取消', exact=True).click()
        page.get_by_role('button', name='删除', exact=True).nth(1).click()
        deletion.get_by_role('button', name='确认删除', exact=True).click(); settle()
        expect(deletion).not_to_be_visible()

        for kind in ['ssh', 'docker']:
            open_panel(kind)
            page.get_by_role('button', name='新增凭证', exact=True).click()
            dialog = page.get_by_role('dialog', name='新增凭证', exact=True)
            dialog.get_by_label('凭证名称', exact=True).fill('demo-created')
            if kind == 'ssh':
                dialog.get_by_label('密码', exact=True).fill('demo-password')
            else:
                dialog.get_by_label('API Key', exact=True).fill('demo-portainer-key')
            dialog.get_by_role('button', name='保存凭证', exact=True).click(); settle()
            expect(dialog).not_to_be_visible()
            assert mutations[-1][0] == 'POST'
        assert page.evaluate('document.body.style.overflow') != 'hidden'
        context.close()

        # Non-admin users never receive the management entry or issue credential requests.
        demo.RESPONSES['/api/managed-hosts/context'] = dict(is_admin=False, actor_type='user', actor_name='demo-user')
        context = browser.new_context(); context.route('**/*', intercept)
        context.add_init_script("localStorage.setItem('auth_token', btoa('demo-user:demo-only'))")
        page = context.new_page(); start = len(queries)
        page.goto(demo.BASE + '/hosts'); settle()
        expect(page.get_by_role('button', name='凭证管理', exact=True)).to_have_count(0)
        assert not any(path.startswith(('/api/ssh-credentials', '/api/docker-credentials')) for path, _ in queries[start:])
        browser.close()
    assert not errors, '\n'.join(errors)
    print('Credential create/edit, secret retention/rotation, in-use deletion, mobile dialogs and admin-only entry passed.', flush=True)


if __name__ == '__main__':
    main()
