"""Mobile list geometry, long values, menus and server-backed host filters."""
from copy import deepcopy
from pathlib import Path
from urllib.parse import urlparse, parse_qs
from playwright.sync_api import sync_playwright, expect
import capture_screenshots as demo


def main():
    errors, queries = [], []
    state = dict(fail_groups=False, fail_hosts=False)
    output = Path(__file__).resolve().parents[2]/'.codex-remote-attachments/usability'
    output.mkdir(parents=True, exist_ok=True)
    for row in demo.PROXIES:
        row.update(name=row['name']+'超长代理名称'*25, group_name='长分组名'*30,
                   local_ip='2001:db8:abcd:1234:5678:9012:3456:7890', client_version='0.61.1-long-build-version')
    for row in demo.GROUPS: row['group_name'] += '超长分组名称'*25
    hosts = deepcopy(demo.HOSTS)
    demo.HOSTS[:] = [{**row, 'id': i+1, 'name': f'host-{i+1}',
        'host_type': 'ssh' if i%2 else 'rdp', 'last_status': 'error' if i%3 else 'online'}
        for i, row in enumerate((hosts*7)[:36])]
    demo.RESPONSES['/api/managed-hosts'] = demo.HOSTS

    def intercept(route):
        u=urlparse(route.request.url)
        if u.netloc != '127.0.0.1:4173': errors.append('External request'); route.abort(); return
        if not u.path.startswith('/api/'): route.continue_(); return
        if route.request.method != 'GET': errors.append('Unexpected write '+u.path); route.fulfill(status=500,json={}); return
        if u.path == '/api/groups' and state['fail_groups']:
            route.fulfill(status=503,json=dict(detail='分组读取演示失败')); return
        if u.path == '/api/managed-hosts':
            queries.append(parse_qs(u.query))
            if state['fail_hosts']: route.fulfill(status=503,json=dict(detail='主机读取演示失败')); return
        data=demo.demo_response(u)
        if data is None: errors.append('Missing fixture '+u.path)
        route.fulfill(json=data or {})

    with sync_playwright() as p:
        browser=p.chromium.launch()
        ctx=browser.new_context(reduced_motion='reduce',locale='zh-CN')
        ctx.route('**/*',intercept)
        ctx.add_init_script("localStorage.setItem('auth_token',btoa('demo-admin:demo-only'));localStorage.setItem('currentServerId','1')")
        page=ctx.new_page(); page.on('pageerror',lambda e:errors.append(str(e)))

        def settle():
            page.wait_for_load_state('networkidle')
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), page.url

        def navigate(name):
            page.get_by_role('button',name='切换导航菜单',exact=True).click()
            page.get_by_role('navigation',name='主导航').get_by_role('link',name=name,exact=True).click()
            settle()

        def geometry(cards,height):
            expect(cards.first).to_be_visible()
            boxes=cards.evaluate_all('''els=>els.map(el=>{
              const b=el.getBoundingClientRect();return {h:b.height, fits:el.scrollWidth<=el.clientWidth && el.scrollHeight<=el.clientHeight,
              buttons:[...el.querySelectorAll('button')].every(x=>{const r=(x.getAttribute('role')==='checkbox'?x.closest('label'):x).getBoundingClientRect();return r.height>=44 && r.left>=b.left && r.right<=b.right && r.bottom<=b.bottom})};})''')
            assert all(x['h']==height and x['fits'] and x['buttons'] for x in boxes),boxes

        for width in [320,360,390,430,767]:
            page.set_viewport_size(dict(width=width,height=844))
            page.goto(demo.BASE+'/proxies');settle()
            geometry(page.locator('article:visible'),352)
            card=page.locator('article:visible').first
            card.get_by_role('checkbox').check();expect(card.get_by_role('checkbox')).to_be_checked()
            card.get_by_role('button',name='代理操作',exact=True).click()
            expect(page.get_by_role('menuitem',name='删除代理',exact=True)).to_be_visible()
            page.keyboard.press('Escape')
            if width==390: page.screenshot(path=str(output/'proxy-mobile.png'))
            navigate('分组管理')
            geometry(page.locator('li[data-group-name]:visible'),208)
            page.locator('li[data-group-name]:visible').first.get_by_role('button',name='更多操作',exact=True).click()
            page.get_by_role('menuitem',name='重命名',exact=True).click()
            page.get_by_role('dialog').get_by_role('button',name='取消',exact=True).click()
            if width==390: page.screenshot(path=str(output/'groups-mobile.png'))
            navigate('主机资源')
            page.get_by_role('link',name='连接服务、授权与审计',exact=True).click();settle()
            page.get_by_role('combobox',name='主机类型',exact=True).click()
            page.get_by_role('option',name='SSH',exact=True).click();settle()
            assert queries[-1]['host_type']==['ssh']
            expect(page.locator('article')).to_have_count(18)
            page.get_by_role('combobox',name='主机状态',exact=True).click()
            page.get_by_role('option',name='检查异常',exact=True).click();settle()
            assert queries[-1]['host_status']==['abnormal']
            expect(page.locator('article')).to_have_count(12)
            assert 'host_type=ssh' in page.url and 'host_status=abnormal' in page.url
            if width==390: page.screenshot(path=str(output/'hosts-filters-mobile.png'))
            page.locator('article').first.get_by_role('heading',level=2).get_by_role('link').click();settle()
            page.get_by_role('link',name='← 返回连接列表',exact=True).click();settle()
            expect(page.locator('article')).to_have_count(12)
            page.get_by_role('button',name='清除筛选',exact=True).click();settle()
            expect(page.locator('article')).to_have_count(20)
            assert 'host_type' not in queries[-1] and 'host_status' not in queries[-1]
            print(f'Mobile cards and combined host filters passed: {width}px',flush=True)
        page.set_viewport_size(dict(width=1280,height=900))
        page.goto(demo.BASE+'/hosts?page=2&page_size=10&host_type=ssh');settle()
        expect(page.locator('article')).to_have_count(8)
        assert queries[-1]['page']==['2'] and queries[-1]['page_size']==['10']
        state['fail_hosts']=True
        page.get_by_role('button',name='查询',exact=True).click();settle()
        expect(page.get_by_role('alert')).to_contain_text('主机读取演示失败')
        expect(page.get_by_text('暂无主机',exact=False)).to_have_count(0)
        state['fail_hosts']=False
        page.get_by_role('button',name='查询',exact=True).click();settle()
        expect(page.locator('article')).to_have_count(10)
        state['fail_groups']=True
        page.get_by_role('navigation',name='主导航').get_by_role('link',name='分组管理',exact=True).click()
        expect(page.get_by_role('button',name='重试读取分组',exact=True)).to_be_visible()
        expect(page.get_by_role('alert')).to_contain_text('分组读取演示失败')
        expect(page.get_by_text('暂无分组，请先创建分组或导入配置',exact=True)).to_have_count(0)
        state['fail_groups']=False
        page.get_by_role('button',name='重试读取分组',exact=True).click()
        expect(page.locator('tbody tr')).to_have_count(3)
        browser.close()
    assert not errors,errors


if __name__=='__main__': main()
