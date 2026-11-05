"""Explicit built-in service power controls; all mutations use local fixtures."""
from urllib.parse import urlparse
from playwright.sync_api import sync_playwright, expect
import capture_screenshots as demo


def main():
    config=dict(available=True,enabled=False,running=False,onboarding_seen=True,
        public_addr='frp.example.com',bind_port=7100,dashboard_port=7500,proxy_port_start=6000,proxy_port_end=6099)
    state=dict(admin=True,hold=False)
    changes,pending,errors=[],[],[]
    def intercept(route):
        u=urlparse(route.request.url)
        if u.netloc!='127.0.0.1:4173':errors.append('External request');route.abort();return
        if not u.path.startswith('/api/'):route.continue_();return
        if u.path=='/api/settings/user':
            route.fulfill(json=dict(username='demo-admin',role='admin' if state['admin'] else 'user'));return
        if u.path=='/api/builtin-frps':
            if route.request.method=='PUT':
                body=route.request.post_data_json
                assert set(body)==({'enabled','public_addr'} if body['enabled'] else {'enabled'}),body
                assert not body['enabled'] or body['public_addr']=='frp.example.com'
                changes.append(body)
                if state['hold']:pending.append(route);return
                config.update(enabled=body['enabled'],running=body['enabled'])
            route.fulfill(json=config);return
        if u.path=='/api/builtin-frps/raw-config/preview':
            route.fulfill(json=dict(content='bindPort = 7100\n',revision='demo',changed=False));return
        if route.request.method!='GET':errors.append('Unexpected write '+u.path);route.fulfill(status=501,json={});return
        data=demo.demo_response(u)
        if data is None:errors.append('Missing fixture '+u.path)
        route.fulfill(json=data or {})
    with sync_playwright() as p:
        b=p.chromium.launch();ctx=b.new_context(has_touch=True,is_mobile=True,reduced_motion='reduce')
        ctx.add_init_script("localStorage.setItem('auth_token',btoa('demo-admin:demo-only'))")
        ctx.route('**/*',intercept)
        page=ctx.new_page();page.on('pageerror',lambda e:errors.append(str(e)))
        for width in [320,390,1280]:
            config.update(enabled=False,running=False)
            page.set_viewport_size(dict(width=width,height=844))
            page.goto(demo.BASE+'/tunnel-services?tab=builtin')
            start=page.get_by_role('button',name='启用服务',exact=True)
            expect(start).to_be_enabled()
            address=page.get_by_label('公网 IP / 域名',exact=True);address.fill('draft.example.com')
            start.click();stop=page.get_by_role('button',name='关闭服务',exact=True)
            expect(stop).to_be_enabled();expect(address).to_have_value('draft.example.com')
            assert config['bind_port']==7100
            count=len(changes);stop.click()
            dialog=page.get_by_role('alertdialog',name='关闭内置 FRP',exact=True)
            expect(dialog).to_contain_text('所有客户端和代理连接')
            for impact in ['SSH','RDP 远程桌面','其他穿透节点不受影响','重新启用服务','frpc']:expect(dialog).to_contain_text(impact)
            assert dialog.evaluate('el=>el.scrollWidth<=el.clientWidth')
            dialog.get_by_role('button',name='取消',exact=True).click()
            assert len(changes)==count
            state['hold']=True;stop.click();dialog.get_by_role('button',name='关闭服务',exact=True).click()
            expect(stop).to_be_disabled()
            assert len(changes)==count+1
            pending.pop().fulfill(status=503,json=dict(detail='演示关闭失败'))
            expect(page.get_by_role('alert')).to_contain_text('演示关闭失败')
            expect(stop).to_be_enabled();expect(address).to_have_value('draft.example.com')
            state['hold']=False;stop.click();dialog.get_by_role('button',name='关闭服务',exact=True).click()
            expect(start).to_be_enabled();expect(address).to_have_value('draft.example.com')
            start.click();expect(stop).to_be_enabled()
            page.get_by_role('tab',name='原始配置文件',exact=True).click()
            editor=page.locator('.cm-content').first;expect(editor).to_be_visible()
            editor.fill('# unsaved draft\nbindPort = 7200')
            stop.click();dialog.get_by_role('button',name='关闭服务',exact=True).click()
            expect(start).to_be_enabled();expect(editor).to_contain_text('unsaved draft')
            assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
            print(f'Builtin enable, close/cancel/failure/retry, saved-config scope and draft preservation passed: {width}px',flush=True)
        state['admin']=False;page.reload()
        expect(page.get_by_role('tab',name='服务节点',exact=True)).to_be_visible()
        expect(page.get_by_role('button',name='启用服务',exact=True)).to_have_count(0)
        expect(page.get_by_role('button',name='关闭服务',exact=True)).to_have_count(0)
        b.close()
    assert not errors,errors


if __name__=='__main__':main()
