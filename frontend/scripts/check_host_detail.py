"""Read-only host drilldown: scoped logs/traffic, detail output, retry and access."""
from copy import deepcopy
from pathlib import Path
from urllib.parse import urlparse, parse_qs
from playwright.sync_api import sync_playwright, expect
import capture_screenshots as demo


def main():
    state = dict(admin=True, fail_host=False, fail_logs=False)
    errors, queries, cleanup_previews = [], [], []
    hosts = deepcopy(demo.HOSTS)
    hosts[0]['description'] = '连接与所属主机'
    logs = [dict(id=100+i, host_id=1, host_name=hosts[0]['name'], actor_name='operator' if i % 2 else 'other-admin',
        actor_type='user', created_at=demo.DATE, action='execute_command', command=f'host-one-only-{i}',
        status='success', stdout='DEMO OUTPUT\nSecond line', stderr='DEMO STDERR', exit_code=0,
        duration_ms=22, bytes_sent=100, bytes_received=200, client_ip='192.0.2.10') for i in range(23)]
    logs.append({**logs[0], 'id': 999, 'host_id': 2, 'host_name': hosts[1]['name'], 'command': 'host-two-only'})
    output = Path(__file__).resolve().parents[2] / '.codex-remote-attachments/usability'
    output.mkdir(parents=True, exist_ok=True)

    def intercept(route):
        u = urlparse(route.request.url); q = parse_qs(u.query)
        if u.netloc != '127.0.0.1:4173':
            errors.append('Unexpected external request'); route.abort(); return
        if not u.path.startswith('/api/'):
            route.continue_(); return
        if u.path == '/api/managed-hosts/audit/cleanup':
            body = route.request.post_data_json
            assert body['dry_run'] and body['host_id'] == 1, body
            cleanup_previews.append(body); route.fulfill(json=dict(count=3)); return
        if route.request.method != 'GET':
            errors.append('Unexpected mutation: '+u.path); route.fulfill(status=500,json={}); return
        if u.path == '/api/settings/user':
            route.fulfill(json=dict(username='operator',role='admin' if state['admin'] else 'user')); return
        if u.path == '/api/managed-hosts/context':
            route.fulfill(json=dict(is_admin=state['admin'],actor_type='user',actor_name='operator')); return
        if u.path == '/api/managed-hosts':
            if state['fail_host']:
                route.fulfill(status=503,json=dict(detail='主机读取演示失败')); return
            rows = [h for h in hosts if state['admin'] or h['id'] == 1]
            if q.get('host_id'): rows = [h for h in rows if str(h['id']) == q['host_id'][0]]
            if q.get('search'): rows = [h for h in rows if q['search'][0] in h['name']]
            rows = [{**h,'can_manage':state['admin']} for h in rows]
            page = int(q.get('page',['1'])[0]); size=int(q.get('page_size',['20'])[0])
            route.fulfill(json=dict(items=rows[(page-1)*size:page*size],total=len(rows),page=page,page_size=size)); return
        if u.path in ['/api/managed-hosts/audit/logs','/api/managed-hosts/audit/traffic']:
            queries.append((u.path,q))
            assert q.get('host_id') == ['1'], ('Query lost host scope',q)
            if state['fail_logs']:
                route.fulfill(status=503,json=dict(detail='日志读取演示失败')); return
            rows = [r for r in logs if r['host_id'] == 1 and (state['admin'] or r['actor_name']=='operator')]
            if q.get('search'): rows = [r for r in rows if q['search'][0] in r['command']]
            if u.path.endswith('/traffic'):
                route.fulfill(json=dict(bytes_sent=len(rows)*100,bytes_received=len(rows)*200,measured_count=len(rows),record_count=len(rows))); return
            page = int(q.get('page',['1'])[0]); size = int(q.get('page_size',['20'])[0])
            route.fulfill(json=dict(items=rows[(page-1)*size:page*size],total=len(rows),page=page,page_size=size)); return
        if u.path.startswith('/api/managed-hosts/audit/logs/'):
            row = next(r for r in logs if r['id']==int(u.path.rsplit('/',1)[1]))
            assert state['admin'] or row['actor_name']=='operator'
            route.fulfill(json=row); return
        data = demo.demo_response(u)
        if data is None: errors.append('Missing fixture: '+u.path)
        route.fulfill(json=data or {})

    with sync_playwright() as p:
        browser = p.chromium.launch()
        context = browser.new_context(locale='zh-CN',reduced_motion='reduce')
        context.route('**/*',intercept)
        context.add_init_script("localStorage.setItem('auth_token',btoa('operator:demo-only'))")
        page=context.new_page(); page.on('pageerror',lambda e:errors.append(str(e)))

        def settle():
            page.wait_for_load_state('networkidle')
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), page.url

        for width in [1280,390,320,768]:
            page.set_viewport_size(dict(width=width,height=900))
            page.goto(demo.BASE+'/hosts'); settle()
            search=page.get_by_role('textbox',name='搜索主机',exact=True)
            search.fill(hosts[0]['name']); search.press('Enter'); settle()
            page.get_by_role('link',name=hosts[0]['name'],exact=True).click(); settle()
            expect(page.locator('main h1')).to_have_text(hosts[0]['name'])
            expect(page.get_by_text('连接与所属主机',exact=True)).to_be_visible()
            expect(page.get_by_text('关联凭据',exact=True)).to_be_visible()
            page.get_by_role('link',name='← 返回连接列表',exact=True).click(); settle()
            expect(page.get_by_role('textbox',name='搜索主机',exact=True)).to_have_value(hosts[0]['name'])
            page.get_by_role('link',name='查看主机日志',exact=True).click(); settle()
            expect(page.get_by_role('tab',name='日志与流量',exact=True)).to_have_attribute('aria-selected','true')
            expect(page.get_by_role('combobox',name='筛选主机',exact=True)).to_have_count(0)
            expect(page.locator('main')).not_to_contain_text('host-two-only')
            page.get_by_role('button',name='下一页',exact=True).click(); settle()
            assert any(q.get('page')==['2'] for path,q in queries if path.endswith('/logs'))
            page.get_by_role('button',name='重置',exact=True).click(); settle()
            page.get_by_role('combobox',name='每页条数',exact=True).click()
            page.get_by_role('option',name='10',exact=True).click(); settle()
            expect(page.locator('main')).not_to_contain_text('host-two-only')
            page.get_by_role('button',name='详情',exact=True).first.click(); settle()
            dialog=page.get_by_role('dialog')
            expect(dialog).to_contain_text('DEMO OUTPUT')
            expect(dialog).to_contain_text('DEMO STDERR')
            assert dialog.evaluate('el => el.scrollWidth <= el.clientWidth')
            if width < 768:
                page.set_viewport_size(dict(width=width,height=420))
                dialog.get_by_role('button',name='关闭详情',exact=True).click(trial=True)
                page.set_viewport_size(dict(width=width,height=900))
            dialog.get_by_role('button',name='关闭详情',exact=True).click()
            page.get_by_role('button',name='清理旧日志',exact=True).click()
            page.get_by_role('button',name='预览影响数量',exact=True).click(); settle()
            page.get_by_role('dialog').get_by_role('button',name='关闭',exact=True).click()
            page.screenshot(path=str(output/f'host-log-detail-{width}.png'))
            print(f'Host drilldown, pinned filters, paging and log output passed: {width}px',flush=True)

        state['fail_logs']=True
        page.get_by_role('button',name='刷新',exact=True).click(); settle()
        expect(page.get_by_role('alert')).to_contain_text('日志读取演示失败')
        expect(page.get_by_text('暂无审计记录',exact=True)).to_have_count(0)
        state['fail_logs']=False
        page.get_by_role('button',name='刷新',exact=True).click(); settle()
        expect(page.get_by_role('alert')).to_have_count(0)
        state['fail_host']=True; page.reload(); settle()
        expect(page.get_by_role('alert')).to_contain_text('主机读取演示失败')
        count=len(queries); state['fail_host']=False
        page.get_by_role('button',name='重试读取主机',exact=True).click(); settle()
        expect(page.get_by_role('tab',name='日志与流量',exact=True)).to_have_attribute('aria-selected','true')
        expect(page.get_by_role('button',name='详情',exact=True).first).to_be_visible()
        assert len(queries)>count, (page.url,page.locator('main').inner_text())
        state['admin']=False; page.reload(); settle()
        expect(page.get_by_role('link',name='编辑连接',exact=True)).to_have_count(0)
        expect(page.get_by_role('button',name='清理旧日志',exact=True)).to_have_count(0)
        expect(page.locator('main')).to_contain_text('仅显示你本人的访问与操作记录')
        expect(page.locator('main')).not_to_contain_text('other-admin')
        before=len(queries)
        page.goto(demo.BASE+'/hosts/2?tab=logs'); settle()
        expect(page.get_by_role('alert')).to_contain_text('主机不存在或当前账号无权查看')
        assert len(queries)==before, 'Denied hosts must not load any audit data'
        browser.close()
    assert cleanup_previews and queries
    assert not errors, errors
    print('Scoped logs/traffic, output details, failure/retry and ordinary-user access passed.',flush=True)


if __name__=='__main__': main()
