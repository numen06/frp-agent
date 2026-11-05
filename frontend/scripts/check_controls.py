"""Exercise shared shadcn controls against isolated, paginated demo APIs."""
from urllib.parse import urlparse, parse_qs
from pathlib import Path
from playwright.sync_api import sync_playwright, expect
import capture_screenshots as demo


def main():
    errors, calls = [], []
    state = dict(fail_groups=False)
    groups = [f'group-{i:02}' for i in range(1, 44)]
    proxies = [{**demo.PROXIES[i % len(demo.PROXIES)], 'id': i + 1, 'name': f'proxy-{i+1}'} for i in range(43)]

    def intercept(route):
        u = urlparse(route.request.url)
        if u.netloc != '127.0.0.1:4173':
            errors.append('External request'); route.abort(); return
        if not u.path.startswith('/api/'):
            route.continue_(); return
        q = parse_qs(u.query); calls.append((u.path, q))
        if route.request.method != 'GET':
            errors.append('Unexpected write: ' + u.path); route.fulfill(status=500, json={}); return
        if u.path == '/api/groups/list':
            if state['fail_groups']:
                route.fulfill(status=503, json=dict(detail='演示选项加载失败')); return
            rows = [g for g in groups if q.get('search', [''])[0] in g]
            page = int(q.get('page', ['1'])[0]); size = int(q.get('page_size', ['20'])[0])
            route.fulfill(json=dict(items=rows[(page-1)*size:page*size], total=len(rows), page=page)); return
        if u.path == '/api/proxies':
            rows = proxies
            page = int(q.get('page', ['1'])[0]); size = int(q.get('page_size', ['20'])[0])
            route.fulfill(json=dict(items=rows[(page-1)*size:page*size], total=len(rows), page=page, page_size=size)); return
        data = demo.demo_response(u)
        if data is None: errors.append('Missing fixture: ' + u.path)
        route.fulfill(json=data or {})

    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport=dict(width=1280, height=900), reduced_motion='reduce', locale='zh-CN')
        ctx.route('**/*', intercept)
        ctx.add_init_script("localStorage.setItem('auth_token',btoa('demo-admin:demo-only'));localStorage.setItem('currentServerId','1')")
        page = ctx.new_page(); page.on('pageerror', lambda e: errors.append(str(e)))
        page.goto(demo.BASE+'/proxies'); page.wait_for_load_state('networkidle')
        # Select supports string filters, keyboard selection, and clearing with null.
        select = page.get_by_role('combobox', name='全部状态', exact=True)
        select.click(); page.get_by_role('option', name='在线', exact=True).click()
        expect(select).to_contain_text('在线')
        select.click(); page.get_by_role('option', name='全部状态', exact=True).click()
        expect(select).to_contain_text('全部状态')
        size = page.get_by_role('combobox', name='每页条数', exact=True)
        size.click(); page.get_by_role('option', name='10', exact=True).click()
        page.wait_for_load_state('networkidle'); expect(size).to_contain_text('10')
        page.get_by_role('button', name='下一页', exact=True).click(); page.wait_for_load_state('networkidle')
        assert any(path == '/api/proxies' and q.get('page') == ['2'] and q.get('page_size') == ['10'] for path, q in calls)
        # Combobox: pagination stays reachable, retains off-page selection, searches remotely, clears.
        group = page.get_by_role('button', name='全部分组', exact=True)
        group.click(); popup = page.locator('[data-slot=combobox-content]')
        expect(popup.get_by_role('option', name='group-01', exact=True)).to_be_visible()
        popup.get_by_role('button', name='下一页选项', exact=True).click()
        popup.get_by_role('option', name='group-21', exact=True).click()
        expect(group).to_contain_text('group-21')
        group.click(); expect(group).to_contain_text('group-21')
        search = popup.get_by_role('combobox')
        search.fill('group-43'); popup.get_by_role('option', name='group-43', exact=True).click()
        expect(group).to_contain_text('group-43')
        group.click(); popup.get_by_role('option', name='全部分组', exact=True).click()
        expect(group).to_contain_text('全部分组')
        state['fail_groups'] = True; group.click()
        expect(popup.get_by_role('alert')).to_contain_text('演示选项加载失败')
        state['fail_groups'] = False; popup.get_by_role('button', name='重试', exact=True).click()
        expect(popup.get_by_role('option', name='group-01', exact=True)).to_be_visible()
        search.press('Escape'); expect(popup).to_have_count(0)
        # Standard menu keyboard dismissal restores focus; choosing an action opens a dialog.
        menu = page.get_by_role('button', name='添加菜单', exact=True)
        menu.focus(); menu.press('ArrowDown'); expect(page.get_by_role('menu')).to_be_visible()
        page.keyboard.press('Escape'); expect(menu).to_be_focused()
        menu.click(); page.get_by_role('menuitem', name='添加代理', exact=True).click()
        dialog = page.get_by_role('dialog'); expect(dialog).to_be_visible()
        expect(page.get_by_role('menu')).to_have_count(0)
        dialog.get_by_role('button', name='关闭', exact=True).click()
        # Checkbox emits actual boolean selection, and changing server clears a group scoped to it.
        page.get_by_role('checkbox').first.check(); expect(page.get_by_text('已选择 10 个代理', exact=True).first).to_be_visible()
        page.get_by_role('checkbox').first.uncheck()
        group.click(); popup.get_by_role('option', name='group-01', exact=True).click()
        page.get_by_role('button', name='选择服务器', exact=True).click()
        popup.get_by_role('option', name='华北 · 业务节点', exact=True).click()
        expect(group).to_contain_text('全部分组')
        # Drawer uses modal focus / scroll handling; selected nested routes stay active.
        page.set_viewport_size(dict(width=390, height=844))
        toggle = page.get_by_role('button', name='切换导航菜单', exact=True)
        toggle.click(); nav = page.get_by_role('navigation', name='主导航')
        expect(nav).to_be_visible(); page.keyboard.press('Escape'); expect(nav).not_to_be_visible()
        expect(toggle).to_be_focused(); toggle.click(); nav.get_by_role('link', name='主机资源', exact=True).click()
        expect(page).to_have_url(demo.BASE+'/hosts'); expect(nav).not_to_be_visible()
        assert page.get_by_role('tablist', name='主机管理分类').evaluate("el => getComputedStyle(el).overflowY === 'hidden'")
        # Toggle group changes the editor's actual host fields, not just its appearance.
        page.get_by_role('button', name='添加主机', exact=True).click()
        page.get_by_role('button', name='Docker 主机', exact=True).click()
        expect(page.get_by_label('连接地址', exact=True)).to_be_visible()
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
        browser.close()
    assert not errors, errors
    print('Select, numeric pagination, paged/searchable Combobox, retry/clear/scope, menu/dialog, checkbox and mobile sidebar passed.', flush=True)


if __name__ == '__main__':
    main()
