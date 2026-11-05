"""Host cards keep their geometry with mixed types, permissions and long content."""
from copy import deepcopy
from pathlib import Path
from urllib.parse import urlparse
from playwright.sync_api import sync_playwright, expect
import capture_screenshots as demo


def main():
    rows = deepcopy(demo.HOSTS)
    errors = []
    output = Path(__file__).resolve().parents[2] / '.codex-remote-attachments/usability'
    output.mkdir(parents=True, exist_ok=True)

    def intercept(route):
        url = urlparse(route.request.url)
        if url.netloc != '127.0.0.1:4173':
            errors.append('Unexpected external request'); route.abort(); return
        if not url.path.startswith('/api/'):
            route.continue_(); return
        if route.request.method != 'GET':
            errors.append('Unexpected mutation: ' + url.path)
            route.fulfill(status=500, json={}); return
        if url.path == '/api/managed-hosts':
            route.fulfill(json=demo.paginated(rows)); return
        data = demo.demo_response(url)
        if data is None: errors.append('Missing fixture: ' + url.path)
        route.fulfill(json=data or {})

    with sync_playwright() as p:
        browser = p.chromium.launch()
        context = browser.new_context(reduced_motion='reduce', locale='zh-CN')
        context.route('**/*', intercept)
        context.add_init_script("localStorage.setItem('auth_token',btoa('demo-admin:demo-only'))")
        page = context.new_page()
        page.on('pageerror', lambda error: errors.append(str(error)))

        def settle():
            page.wait_for_load_state('networkidle')
            expect(page.locator('article')).to_have_count(len(rows))
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')

        def geometry():
            return page.locator('article').evaluate_all('''cards => cards.map(card => {
                const box = card.getBoundingClientRect();
                const footer = card.lastElementChild.getBoundingClientRect();
                return {width: box.width, height: box.height, footer: box.bottom-footer.bottom,
                    fits: card.scrollHeight <= card.clientHeight && card.scrollWidth <= card.clientWidth,
                    actionsFit: [...card.querySelectorAll('button')].every(button => {
                        const b=button.getBoundingClientRect();
                        return b.left>=box.left && b.right<=box.right && b.bottom<=box.bottom;
                    })};
            })''')

        for width in [320, 390, 768, 1280, 1920]:
            page.set_viewport_size(dict(width=width, height=1080 if width == 1920 else 844))
            rows[:] = deepcopy(demo.HOSTS)
            page.goto(demo.BASE + '/hosts'); settle()
            baseline = geometry()
            for i, host in enumerate(rows):
                host.update(name=host['name'] + '-long-host-name' * 12,
                    address='long-host-address-' * 15 + '.example.com',
                    version_info='Long OS / Docker version ' * 20,
                    credential_name='长凭据名称' * 30, tags='业务标签 / ' * 40,
                    last_status='error', last_message='连接异常：证书指纹不匹配。' * 30)
                if i == 4: host.update(permissions=[], can_manage=False, version_info='', tags='')
                if i == 5: host.update(is_active=False, last_status='unknown')
            page.reload(); settle()
            current = geometry()
            assert current == baseline, (width, baseline, current)
            assert all(c['fits'] and c['actionsFit'] and c['height'] == 304 for c in current), (width, current)
            assert max(c['width'] for c in current) - min(c['width'] for c in current) < 1
            assert len(set(c['footer'] for c in current)) == 1
            expect(page.locator('article').nth(4).get_by_role('button', name='Web SSH')).to_have_count(0)
            expect(page.locator('article').nth(5).get_by_role('button', name='Web SSH')).to_be_disabled()
            page.locator('article').first.get_by_role('button', name='连接详情', exact=True).click()
            dialog = page.get_by_role('dialog')
            expect(dialog).to_contain_text(rows[0]['version_info'])
            expect(dialog).to_contain_text(rows[0]['last_message'])
            assert dialog.evaluate('el => el.scrollWidth <= el.clientWidth'), width
            dialog.get_by_role('button', name='关闭', exact=True).first.click()
            assert geometry() == current
            print(f'Host geometry stable with long content and mixed permissions: {width}px', flush=True)

        rows[:] = deepcopy(demo.HOSTS)
        page.set_viewport_size(dict(width=1280, height=1000))
        page.reload(); settle()
        page.screenshot(path=str(output / 'host-cards-desktop.png'))
        for action, suffix in [('编辑主机', 'edit'), ('克隆主机', 'clone')]:
            page.locator('article').first.get_by_role('button', name='主机操作', exact=True).click()
            page.get_by_role('menuitem', name=action, exact=True).click()
            expect(page).to_have_url(demo.BASE + '/hosts/1/' + suffix + '?page=1&page_size=20')
            page.get_by_role('navigation', name='主导航').get_by_role('link', name='主机资源', exact=True).click()
            settle()
        page.locator('article').first.get_by_role('button', name='主机操作', exact=True).click()
        page.get_by_role('menuitem', name='删除主机', exact=True).click()
        expect(page.get_by_role('alertdialog')).to_contain_text('production-linux')
        page.get_by_role('alertdialog').get_by_role('button', name='取消', exact=True).click()
        page.locator('article').first.get_by_role('button', name='主机操作', exact=True).click()
        page.get_by_role('menuitem', name='流量与审计', exact=True).click()
        expect(page.get_by_role('tab', name='日志与流量', exact=True)).to_have_attribute('aria-selected', 'true')
        assert '/hosts/1?' in page.url
        browser.close()
    assert not errors, errors
    print('Host details, fixed layout, edit/clone/delete cancellation and audit navigation passed.', flush=True)


if __name__ == '__main__':
    main()
