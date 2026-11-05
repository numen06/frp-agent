"""SPA navigation, real collection contracts, visible actions and RDP preflight."""
from copy import deepcopy
import re
from pathlib import Path
from urllib.parse import urlparse, parse_qs
from playwright.sync_api import sync_playwright, expect
import capture_screenshots as demo
from check_runtime import fixture


def main():
    demo.RESPONSES['/api/system/overview'] = fixture()
    demo.SERVERS[0]['is_builtin'] = True
    state = dict(fail_proxy=False, rdp_ok=False, admin=True, role_error=False, tests=0, downloads=0)
    errors, proxy_queries = [], []
    output = Path(__file__).resolve().parents[2]/'.codex-remote-attachments/usability'
    output.mkdir(parents=True, exist_ok=True)

    def intercept(route):
        u = urlparse(route.request.url); q = parse_qs(u.query)
        if u.netloc != '127.0.0.1:4173':
            errors.append('Unexpected external request'); route.abort(); return
        if not u.path.startswith('/api/'):
            route.continue_(); return
        if u.path == '/api/settings/user':
            if state['role_error']:
                route.fulfill(status=503,json=dict(detail='读取权限演示失败')); return
            route.fulfill(json=dict(username='demo-admin', role='admin' if state['admin'] else 'user')); return
        if u.path == '/api/managed-hosts/context':
            route.fulfill(json=dict(is_admin=state['admin'], actor_type='user', actor_name='demo-admin')); return
        if u.path == '/api/proxies':
            proxy_queries.append(q)
            if state['fail_proxy']:
                route.fulfill(status=503, json=dict(detail='演示接口暂时不可用')); return
            node = q.get('frps_server_id', ['1'])[0]
            rows = [{**r, 'name': f'node{node}_{r["name"]}'} for r in demo.PROXIES]
            if q.get('search'): rows = [r for r in rows if q['search'][0] in r['name']]
            route.fulfill(json=demo.paginated(rows)); return
        if u.path == '/api/managed-hosts/3/test':
            state['tests'] += 1
            route.fulfill(json=dict(success=state['rdp_ok'], duration_ms=25,
                stdout='RDP TLS/NLA 及证书校验通过' if state['rdp_ok'] else '',
                stderr='' if state['rdp_ok'] else 'RDP 证书指纹不匹配，请核验目标机器后重新获取指纹')); return
        if u.path == '/api/managed-hosts/3/rdp-file':
            state['downloads'] += 1
            route.fulfill(body='full address:s:demo.invalid:13389', content_type='application/x-rdp'); return
        if u.path.startswith('/api/groups/') and u.path.endswith('/deploy-preview'):
            route.fulfill(json=dict(command='echo demo-preview', warnings=[], missing_requirements=[])); return
        if route.request.method != 'GET':
            errors.append('Unexpected mutation: '+u.path); route.fulfill(status=500,json={}); return
        data = demo.demo_response(u)
        if data is None: errors.append('Missing fixture: '+u.path)
        route.fulfill(json=data or {})

    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport=dict(width=1280,height=900), reduced_motion='reduce', locale='zh-CN')
        ctx.route('**/*', intercept)
        ctx.add_init_script("localStorage.setItem('auth_token',btoa('demo-admin:demo-only'));localStorage.setItem('currentServerId','1')")
        page = ctx.new_page(); page.on('pageerror',lambda e:errors.append(str(e)))

        def settle():
            page.wait_for_load_state('networkidle')
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), page.url

        def navigate(label):
            nav = page.get_by_role('navigation',name='主导航')
            if page.viewport_size['width'] < 1024:
                page.get_by_role('button',name='切换导航菜单',exact=True).click()
            link=nav.get_by_role('link',name=label,exact=True)
            target=link.get_attribute('href')
            link.click()
            expect(page).to_have_url(demo.BASE+target)
            settle()

        # Regression: loaded server store followed by SPA navigation used to issue ZERO proxy requests.
        page.goto(demo.BASE+'/dashboard'); settle()
        navigate('代理列表')
        expect(page.get_by_text('node1_office_ssh',exact=True).first).to_be_visible()
        assert proxy_queries, 'SPA navigation must fetch proxy data'
        for node in demo.SERVERS:
            page.get_by_role('button',name='选择服务器',exact=True).click()
            page.get_by_role('option',name=node['name'],exact=True).click()
            expect(page.get_by_text(f'node{node["id"]}_office_ssh',exact=True).first).to_be_visible()
        print('Dashboard → proxies and switching all 3 servers fetch their actual collections',flush=True)
        settle()

        edit = page.get_by_role('button',name='编辑',exact=True).first
        assert edit.inner_text().strip() == '', 'Desktop row actions should stay compact'
        for button in [edit, page.get_by_role('button',name='代理操作',exact=True).first]:
            box=button.bounding_box(); assert box and box['x'] >= 0 and box['x']+box['width'] <= page.viewport_size['width'], box
        page.get_by_role('checkbox').first.focus()
        for _ in range(5):
            page.keyboard.press('Tab')
            if edit.evaluate('el => el === document.activeElement'): break
        expect(edit).to_be_focused(); expect(page.get_by_role('tooltip',name='编辑',exact=True)).to_contain_text('编辑')
        page.keyboard.press('Escape'); expect(page.locator('[data-slot=tooltip-content]')).to_have_count(0)
        edit.hover(); expect(page.get_by_role('tooltip',name='编辑',exact=True)).to_contain_text('编辑')
        page.get_by_role('checkbox').first.focus()
        page.mouse.move(5,5); expect(page.locator('[data-slot=tooltip-content]')).to_have_count(0)
        page.keyboard.press('Escape')
        page.get_by_role('button',name='代理操作',exact=True).first.click()
        expect(page.get_by_role('menuitem',name='客户端升级',exact=True)).to_be_visible()
        page.get_by_role('menuitem',name='删除代理',exact=True).click()
        expect(page.get_by_role('alertdialog')).to_contain_text('node3_office_ssh')
        page.get_by_role('alertdialog').get_by_role('button',name='取消',exact=True).click()
        navigate('分组管理')
        page.get_by_role('button',name='更多操作',exact=True).first.click()
        page.get_by_role('menuitem',name='一键部署',exact=True).click()
        expect(page.get_by_role('dialog')).to_be_visible()
        page.get_by_role('dialog').get_by_role('button',name='关闭',exact=True).first.click()
        navigate('代理列表')
        page.keyboard.press('Escape')
        state['fail_proxy']=True; page.get_by_role('button',name='刷新',exact=True).click()
        expect(page.get_by_role('alert')).to_contain_text('保留上次数据')
        state['fail_proxy']=False; page.get_by_role('button',name='重试读取代理',exact=True).click(); expect(page.get_by_role('alert')).to_have_count(0)
        search=page.get_by_role('textbox',name='搜索',exact=True); search.fill('no-such-proxy'); search.press('Enter')
        expect(page.get_by_text('没有符合当前筛选条件的代理，请清除筛选后重试。',exact=True).first).to_be_visible()
        page.get_by_role('button',name='清除筛选',exact=True).click(); expect(page.get_by_text('node3_office_ssh',exact=True).first).to_be_visible()
        page.screenshot(path=str(output/'proxy-actions.png'))

        # Exercise every sidebar route through the existing app instance, not page.goto reloads.
        for label, path in [('分组管理','groups'),('穿透服务','tunnel-services'),('主机资源','machines'),('安装包管理','packages'),('配置转换','converter'),('密钥管理','api-keys'),('运行维护','operations'),('仪表盘','dashboard'),('代理列表','proxies')]:
            navigate(label); expect(page).to_have_url(demo.BASE+'/'+path); expect(page.locator('main h1')).to_have_count(1)
            if path == 'tunnel-services':
                tabs = page.get_by_role('tablist',name='穿透服务分类',exact=True)
                expect(tabs.get_by_role('tab')).to_have_count(2)
                nodes = tabs.get_by_role('tab',name='服务节点',exact=True)
                builtin = tabs.get_by_role('tab',name='内置服务',exact=True)
                expect(nodes).to_have_attribute('aria-selected','true')
                expect(page.get_by_role('navigation',name='主导航').get_by_role('link',name='内置服务',exact=True)).to_have_count(0)
                nodes.focus(); page.keyboard.press('ArrowRight'); settle()
                expect(builtin).to_be_focused()
                expect(builtin).to_have_attribute('aria-selected','true')
                expect(page).to_have_url(demo.BASE+'/tunnel-services?tab=builtin')
                expect(page.get_by_role('heading',name='内置 FRP 服务端',exact=True)).to_be_visible()
                for label in ['安全设置','插件','基础配置']:
                    page.get_by_role('tab',name=label,exact=True).click(); settle()
                builtin.focus(); page.keyboard.press('ArrowLeft'); settle()
                expect(nodes).to_be_focused()
                expect(nodes).to_have_attribute('aria-selected','true')
                expect(page.locator('#builtin-frps')).to_have_count(0)
                for _ in range(2):
                    page.get_by_role('button',name='添加服务器',exact=True).click()
                    page.get_by_role('dialog').get_by_role('button',name='关闭',exact=True).click()
        expect(page.get_by_text('node3_office_ssh',exact=True).first).to_be_visible()

        for width in [1280,390,320]:
            page.set_viewport_size(dict(width=width,height=844))
            if width == 390:
                navigate('代理列表')
                card=page.locator('article').filter(has=page.get_by_text('node3_office_ssh',exact=True))
                expect(card.get_by_role('button',name='编辑',exact=True)).to_be_visible()
                card.get_by_role('button',name='代理操作',exact=True).click()
                expect(page.get_by_role('menuitem',name='客户端升级',exact=True)).to_be_visible()
                page.screenshot(path=str(output/'proxy-compact-mobile-menu.png'))
                page.keyboard.press('Escape')
            navigate('穿透服务')
            expect(page.locator('#builtin-frps')).to_have_count(0)
            page.get_by_role('button',name='服务器操作',exact=True).first.click()
            expect(page.get_by_role('menuitem',name='删除服务器',exact=True)).to_have_count(0)
            page.get_by_role('menuitem',name='配置内置服务',exact=True).click(); settle()
            expect(page).to_have_url(demo.BASE+'/tunnel-services?tab=builtin')
            expect(page.get_by_role('heading',name='内置 FRP 服务端',exact=True)).to_be_visible()
            service_tabs=page.get_by_role('tablist',name='穿透服务分类',exact=True)
            expect(service_tabs.get_by_role('tab')).to_have_count(2)
            if width < 768:
                assert all(t.bounding_box()['height'] >= 44 for t in service_tabs.get_by_role('tab').all())
            page.screenshot(path=str(output/f'tunnel-services-{width}.png'))
            navigate('主机资源')
            page.get_by_role('link',name='连接服务、授权与审计',exact=True).click(); expect(page).to_have_url(re.compile(re.escape(demo.BASE)+r'/hosts(?:\?.*)?$')); settle()
            expect(page.get_by_role('heading',name='production-linux',exact=True)).to_be_visible()
            tabs=page.get_by_role('tablist',name='主机管理分类')
            for label in ['凭证管理','访问授权','系统用户','审计与流量','API 访问','连接服务']:
                tabs.get_by_role('tab',name=label,exact=True).click(); settle()
                if label == '凭证管理':
                    kinds=page.get_by_role('group',name='凭证类型',exact=True)
                    kinds.get_by_role('button',name='Docker / Portainer',exact=True).click(); settle()
                    kinds.get_by_role('button',name='SSH / RDP',exact=True).click(); settle()
            page.screenshot(path=str(output/f'hosts-tabs-{width}.png'))
            card=page.locator('article').filter(has=page.get_by_role('heading',name='office-windows',exact=True))
            expect(card).not_to_contain_text('远程桌面连接说明')
            card.get_by_role('button',name='连接详情',exact=True).click()
            details=page.get_by_role('dialog')
            expect(details).to_contain_text('远程桌面连接说明')
            expect(details).to_contain_text('不验证 Windows 账号登录')
            details.get_by_role('button',name='关闭',exact=True).first.click()
            state['rdp_ok']=False; before=state['downloads']
            card.get_by_role('button',name='下载远程桌面连接',exact=True).click()
            dialog=page.get_by_role('dialog',name='office-windows · RDP 连接未通过',exact=True)
            expect(dialog).to_contain_text('RDP 证书已变化')
            expect(dialog).to_contain_text('与登录密码是否修改无关')
            expect(dialog.get_by_role('button',name='核验并编辑主机',exact=True)).to_be_visible()
            assert state['downloads']==before, 'Failed preflight must never download an RDP file'
            page.screenshot(path=str(output/f'rdp-certificate-warning-{width}.png'))
            state['rdp_ok']=True; dialog.get_by_role('button',name='重新校验 RDP',exact=True).click()
            expect(dialog).to_have_count(0)
            with page.expect_download() as download:
                card.get_by_role('button',name='下载远程桌面连接',exact=True).click()
            download.value.delete(); assert state['downloads']==before+1
        state['role_error']=True
        page.goto(demo.BASE+'/tunnel-services?tab=builtin'); settle()
        expect(page.get_by_role('alert')).to_contain_text('读取权限演示失败')
        expect(page.locator('#builtin-frps')).to_have_count(0)
        state['role_error']=False
        page.get_by_role('button',name='重试读取权限',exact=True).click(); settle()
        expect(page.get_by_role('heading',name='内置 FRP 服务端',exact=True)).to_be_visible()
        navigate('主机资源')
        page.get_by_role('link',name='连接服务、授权与审计',exact=True).click(); expect(page).to_have_url(re.compile(re.escape(demo.BASE)+r'/hosts(?:\?.*)?$')); settle()
        state['admin']=False; page.reload(); settle()
        expect(page.get_by_role('tab',name='凭证管理',exact=True)).to_have_count(0)
        state['rdp_ok']=False
        page.screenshot(path=str(output/'ordinary-services.png'))
        card.get_by_role('button',name='下载远程桌面连接',exact=True).click()
        expect(dialog).to_contain_text('请联系管理员')
        expect(dialog.get_by_role('button',name='核验并编辑主机',exact=True)).to_have_count(0)
        page.goto(demo.BASE+'/builtin-service'); settle()
        expect(page).to_have_url(demo.BASE+'/tunnel-services?tab=servers')
        expect(page.get_by_role('tab',name='内置服务',exact=True)).to_have_count(0)
        expect(page.locator('#builtin-frps')).to_have_count(0)
        page.goto(demo.BASE+'/tunnel-services?tab=builtin'); settle()
        expect(page).to_have_url(demo.BASE+'/tunnel-services?tab=servers')
        expect(page.get_by_role('tab',name='服务节点',exact=True)).to_have_attribute('aria-selected','true')
        browser.close()
    assert not errors, errors
    print('All sidebar routes, host tabs/filter layout, hover/focus action labels, API failure/retry, RDP preflight and non-admin guidance passed.',flush=True)


if __name__=='__main__': main()
