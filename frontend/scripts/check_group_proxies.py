"""Exercise the actual group drilldown, including nested dialogs and late responses."""
from pathlib import Path
from urllib.parse import urlparse,parse_qs
from playwright.sync_api import sync_playwright,expect
import capture_screenshots as demo


def main():
    group='office-'*16+'a'
    rows=[{**demo.PROXIES[0],'id':i,'name':f'proxy-{i}-'+('long-name-'*20),'group_name':group,
        'status':'online' if i%2 else 'offline','local_ip':'2001:db8:1234:5678:9012:3456:7890:abcd',
        'client_version':'0.61.1-'+('long-version-'*10)} for i in range(1,44)]
    groups=[dict(group_name=group,total_count=43,online_count=22,offline_count=21),dict(group_name='other',total_count=1,online_count=1,offline_count=0)]
    other={**demo.PROXIES[0],'id':100,'name':'other-only','group_name':'other'}
    state=dict(fail=False,hold=False)
    queries,pending,writes,errors=[],[],[],[]
    out=Path(__file__).resolve().parents[2]/'.codex-remote-attachments/group-proxies'
    out.mkdir(parents=True,exist_ok=True)
    def intercept(route):
        u=urlparse(route.request.url);q=parse_qs(u.query)
        if u.netloc!='127.0.0.1:4173':errors.append('External request');route.abort();return
        if not u.path.startswith('/api/'):route.continue_();return
        if u.path=='/api/groups':route.fulfill(json=demo.paginated(groups));return
        if u.path=='/api/proxies' and route.request.method=='GET':
            queries.append(q)
            assert q.get('frps_server_id')==['1'],q
            assert q.get('group_name',[None])[0] in [group,'other'],q
            if state['fail']:route.fulfill(status=503,json=dict(detail='演示读取失败'));return
            items=list(rows) if q['group_name']==[group] else [other]
            if q.get('search'):items=[r for r in items if q['search'][0] in r['name']]
            if q.get('status_filter'):items=[r for r in items if r['status']==q['status_filter'][0]]
            page=int(q.get('page',['1'])[0]);size=int(q.get('page_size',['20'])[0])
            payload=dict(items=items[(page-1)*size:page*size],total=len(items),page=page,page_size=size)
            if state['hold'] and q['group_name']==[group]:pending.append((route,payload));return
            route.fulfill(json=payload);return
        if u.path=='/api/proxies/1' and route.request.method=='PUT':
            data=route.request.post_data_json
            assert data['frps_server_id']==1 and data['group_name']==group,data
            rows[0].update(data);writes.append(u.path);route.fulfill(json=rows[0]);return
        if route.request.method!='GET':errors.append('Unexpected write '+u.path);route.fulfill(status=501,json={});return
        payload=demo.demo_response(u)
        if payload is None:errors.append('Missing fixture '+u.path)
        route.fulfill(json=payload or {})
    with sync_playwright() as p:
        b=p.chromium.launch();ctx=b.new_context(reduced_motion='reduce',locale='zh-CN',has_touch=True,is_mobile=True)
        ctx.route('**/*',intercept);ctx.add_init_script("localStorage.setItem('auth_token',btoa('demo-admin:demo-only'));localStorage.setItem('currentServerId','1')")
        page=ctx.new_page();page.set_default_timeout(8000);page.on('pageerror',lambda e:errors.append(str(e)))
        def settle():page.wait_for_load_state('networkidle')
        def parent():return page.get_by_role('dialog',name='查看代理 - '+group,exact=True)
        def open_group(name=group):
            page.locator('li[data-group-name]').filter(has_text=name).get_by_role('button',name='查看代理',exact=True).click()
            dialog=page.get_by_role('dialog',name='查看代理 - '+name,exact=True);expect(dialog).to_be_visible();return dialog
        def geometry(dialog):
            assert dialog.evaluate('el=>el.scrollWidth<=el.clientWidth+1')
            for button in dialog.locator('button:visible').all():
                assert button.evaluate('el=>el.scrollWidth<=el.clientWidth+1 && el.scrollHeight<=el.clientHeight+1'),button.inner_text()
            if page.viewport_size['width']<768:
                boxes=dialog.locator('article').evaluate_all('els=>els.map(el=>({h:el.getBoundingClientRect().height,fits:el.scrollWidth<=el.clientWidth && el.scrollHeight<=el.clientHeight}))')
                assert boxes and all(c['h']==352 and c['fits'] for c in boxes),boxes
        for width in [320,390,430,767,1280]:
            page.set_viewport_size(dict(width=width,height=844));page.goto(demo.BASE+'/groups');settle()
            if width>=768:
                page.locator('tr[data-group-name]').filter(has_text=group).get_by_role('button',name='查看代理',exact=True).click()
            else:open_group()
            dialog=parent();settle();geometry(dialog)
            if width==390:page.screenshot(path=str(out/'mobile.png'))
            dialog.get_by_role('combobox',name='全部状态',exact=True).click();page.get_by_role('option',name='离线',exact=True).click();settle()
            assert queries[-1]['status_filter']==['offline']
            dialog.get_by_role('button',name='下一页',exact=True).click();settle()
            assert queries[-1]['page']==['2']
            if width<768:expect(dialog.locator('article')).to_have_count(1)
            dialog.get_by_role('button',name='清除筛选',exact=True).click();settle()
            assert queries[-1]['group_name']==[group] and 'status_filter' not in queries[-1]
            search=dialog.get_by_role('textbox',name='搜索分组代理',exact=True)
            search.fill('no-match');search.press('Enter');settle()
            empty=dialog.get_by_text('当前分组没有符合筛选条件的代理',exact=True)
            expect(empty.last if width<768 else empty.first).to_be_visible()
            dialog.get_by_role('button',name='清除筛选',exact=True).click();settle()
            state['fail']=True;dialog.get_by_role('button',name='刷新',exact=True).click();settle()
            expect(dialog.get_by_role('alert')).to_contain_text('演示读取失败')
            expect(dialog.get_by_text('当前分组暂无代理',exact=True)).to_have_count(0)
            state['fail']=False;dialog.get_by_role('button',name='重试读取代理',exact=True).click();settle();geometry(dialog)
            dialog.get_by_role('button',name='同步',exact=True).click();settle()
            assert queries[-1].get('sync_from_frps')==['true'] and queries[-1]['group_name']==[group]
            if width==320:
                dialog.get_by_role('button',name='添加',exact=True).click()
                child=page.get_by_role('dialog',name='添加代理',exact=True)
                expect(child.get_by_role('textbox',name='分组名称',exact=True)).to_have_value(group)
                child.get_by_role('button',name='取消',exact=True).click();geometry(dialog)
                dialog.locator('article').first.get_by_role('button',name='编辑',exact=True).click()
                child=page.get_by_role('dialog',name='编辑代理',exact=True)
                child.get_by_role('textbox',name='代理名称',exact=True).fill('edited-group-proxy')
                child.get_by_role('button',name='保存',exact=True).click();settle()
                expect(dialog.locator('article').first).to_contain_text('edited-group-proxy')
                dialog.locator('article').first.get_by_role('button',name='代理操作',exact=True).click()
                page.get_by_role('menuitem',name='删除代理',exact=True).click()
                page.get_by_role('alertdialog').get_by_role('button',name='取消',exact=True).click()
                assert writes==['/api/proxies/1']
            dialog.get_by_role('button',name='关闭',exact=True).first.click()
            print(f'Group drilldown, scoped filters/paging, failure/retry and button/card geometry passed: {width}px',flush=True)
        page.set_viewport_size(dict(width=390,height=844))
        state['hold']=True;open_group();expect(parent().get_by_text('加载中...',exact=True).last).to_be_visible()
        parent().get_by_role('button',name='关闭',exact=True).first.click()
        current=open_group('other');expect(current.locator('article')).to_have_count(1)
        for route,payload in pending:route.fulfill(json=payload)
        state['hold']=False;settle()
        expect(current.locator('article')).to_have_count(1);expect(current).to_contain_text('other-only')
        current.get_by_role('button',name='关闭',exact=True).first.click()
        b.close()
    assert not errors,errors
    print('Nested add/edit/cancel, inherited group, late-response isolation and reopen passed.',flush=True)


if __name__=='__main__':main()
