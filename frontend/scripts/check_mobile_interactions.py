"""Mobile menus, long options, filters, cancellation, failures and conversion.

All requests are intercepted locally; no production writes or credentials.
"""
from pathlib import Path
from urllib.parse import urlparse
from playwright.sync_api import sync_playwright, expect
import capture_screenshots as demo


def main():
    errors,writes,server_saves,pending_saves=[],[],[],[]
    state=dict(fail='',convert_fail=False,hold_save=False)
    long_platform='linux_amd64-'+('long-platform-'*30)
    demo.RESPONSES['/api/packages/platforms']={'platforms':[long_platform,'linux_arm64']}
    demo.PACKAGES[0]['platform']=long_platform
    demo.PACKAGES[0]['filename']='frp-'+('long-filename-'*30)+'.tar.gz'
    out=Path(__file__).resolve().parents[2]/'.codex-remote-attachments/mobile-pages'
    out.mkdir(parents=True,exist_ok=True)

    def intercept(route):
        u=urlparse(route.request.url)
        if u.netloc!='127.0.0.1:4173':errors.append('External request');route.abort();return
        if not u.path.startswith('/api/'):route.continue_();return
        if u.path==state['fail']:
            route.fulfill(status=503,json=dict(detail='演示读取失败，请重试'));return
        if u.path=='/api/frpc/convert/ini-to-toml/direct':
            if state['convert_fail']:route.fulfill(status=422,json=dict(detail='演示转换失败'))
            else:route.fulfill(body='serverAddr = "demo.example.com"\nserverPort = 7000',content_type='text/plain')
            return
        if u.path=='/api/servers/1' and route.request.method=='PUT':
            payload=route.request.post_data_json
            assert 'auth_password' not in payload and 'auth_token' not in payload
            server_saves.append(payload)
            if state['hold_save']:pending_saves.append(route)
            else:route.fulfill(json={**demo.SERVERS[0],**payload})
            return
        if route.request.method!='GET':
            writes.append((route.request.method,u.path));route.fulfill(status=501,json={});return
        if u.path.endswith('/frp-version'):
            route.fulfill(json=dict(server_version='0.61.1',client_versions=[],proxy_count=8));return
        data=demo.demo_response(u)
        if data is None:errors.append('Missing fixture '+u.path)
        route.fulfill(json=data or {})

    with sync_playwright() as p:
        browser=p.chromium.launch()
        ctx=browser.new_context(locale='zh-CN',reduced_motion='reduce',has_touch=True,is_mobile=True)
        ctx.route('**/*',intercept)
        ctx.add_init_script("localStorage.setItem('auth_token',btoa('demo-admin:demo-only'));localStorage.setItem('currentServerId','1')")
        page=ctx.new_page();page.set_default_timeout(8000)
        page.on('pageerror',lambda e:errors.append(str(e)))

        def settle():
            page.wait_for_load_state('networkidle')
            assert page.evaluate('document.documentElement.scrollWidth<=innerWidth'),page.url

        def popup(selector):
            el=page.locator(selector).last;expect(el).to_be_visible()
            page.wait_for_function('s=>{const el=[...document.querySelectorAll(s)].at(-1);const b=el?.getBoundingClientRect();return b && b.left>=0 && b.right<=innerWidth+1 && b.top>=0 && b.bottom<=innerHeight+1}',arg=selector,timeout=2500)
            assert el.evaluate('el=>{const b=el.getBoundingClientRect();return b.left>=0 && b.right<=innerWidth+1 && b.top>=0 && b.bottom<=innerHeight+1}'),selector
            assert el.evaluate('el=>el.scrollWidth<=el.clientWidth+1'),el.evaluate('el=>({slot:el.dataset.slot,width:el.clientWidth,scroll:el.scrollWidth,children:[...el.querySelectorAll("*")].filter(x=>x.getBoundingClientRect().right>el.getBoundingClientRect().right).map(x=>({tag:x.tagName,cls:x.className,w:x.clientWidth,scroll:x.scrollWidth,text:x.textContent.slice(0,55)})).slice(0,12)})')

        def dialog():
            panel=page.get_by_role('dialog');expect(panel).to_be_visible()
            for height in [844,420]:
                page.set_viewport_size(dict(width=width,height=height))
                assert panel.evaluate('el=>el.scrollWidth<=el.clientWidth')
                panel.get_by_role('button',name='关闭',exact=True).first.click(trial=True)
                for button in panel.locator('[data-slot=dialog-footer] button:visible').all():
                    if button.is_enabled():button.click(trial=True)
            page.set_viewport_size(dict(width=width,height=844))
            return panel

        def cancel_confirmation():
            panel=page.get_by_role('alertdialog');expect(panel).to_be_visible()
            assert panel.evaluate('el=>el.scrollWidth<=el.clientWidth')
            panel.get_by_role('button',name='取消',exact=True).click()
            assert not writes,writes

        for width in [320,390,430]:
            page.set_viewport_size(dict(width=width,height=844))
            state['fail']='/api/proxies/dashboard-stats/summary'
            page.goto(demo.BASE+'/dashboard');settle()
            expect(page.get_by_role('alert')).to_contain_text('统计未能完整更新')
            state['fail']='';page.get_by_role('button',name='重试读取概览',exact=True).click();settle()
            expect(page.get_by_role('alert')).to_have_count(0)
            page.goto(demo.BASE+'/packages');settle()
            select=page.get_by_role('combobox',name='全部平台',exact=True)
            select.click();popup('[data-slot=select-content]')
            page.get_by_role('option',name=long_platform,exact=True).click();settle()
            expect(page.locator('.mobile-record:visible')).to_have_count(1)
            page.get_by_role('button',name='清除筛选',exact=True).click();settle()
            expect(page.locator('.mobile-record:visible')).to_have_count(4)
            page.get_by_role('button',name='安装包操作',exact=True).first.click();popup('[data-slot=dropdown-menu-content]')
            page.get_by_role('menuitem',name='删除',exact=True).click();cancel_confirmation()
            page.get_by_role('button',name='脚本生成',exact=True).click()
            panel=dialog();panel.get_by_role('button',name='选择安装包',exact=True).click();popup('[data-slot=combobox-content]')
            page.locator('[data-slot=combobox-content]').get_by_role('combobox').press('Escape')
            panel.get_by_role('button',name='关闭',exact=True).first.click()
            page.get_by_role('button',name='更多安装包管理操作',exact=True).click()
            page.get_by_role('menuitem',name='脚本模板编辑',exact=True).click();panel=dialog()
            panel.get_by_role('combobox',name='目标平台',exact=True).click();popup('[data-slot=select-content]')
            page.keyboard.press('Escape');panel.get_by_role('button',name='关闭',exact=True).first.click()
            state['fail']='/api/packages';page.reload();settle()
            expect(page.get_by_role('alert')).to_contain_text('演示读取失败')
            expect(page.get_by_text('暂无安装包',exact=True)).to_have_count(0)
            state['fail']='';page.get_by_role('button',name='重试读取安装包',exact=True).click();settle()

            for path,retry,empty in [('api-keys','重试读取密钥','暂无 API Key，点击上方按钮创建'),('tunnel-services','重试读取节点','暂无服务器')]:
                state['fail']='/api/api-keys' if path=='api-keys' else '/api/servers'
                page.goto(demo.BASE+'/'+path);settle()
                expect(page.get_by_role('button',name=retry,exact=True)).to_be_visible()
                expect(page.get_by_text(empty,exact=True)).to_have_count(0)
                state['fail']='';page.get_by_role('button',name=retry,exact=True).click();settle()
                search=page.get_by_role('textbox',name='搜索列表',exact=True)
                search.fill('no-match-xyz');search.press('Enter');settle()
                expect(page.get_by_text(empty,exact=True).last).to_be_visible()
                clear=page.get_by_role('button',name='清除搜索',exact=True)
                assert clear.bounding_box()['width']>=44 and clear.bounding_box()['height']>=44
                clear.click();settle()
                card=page.locator('.mobile-record:visible').first
                card.get_by_role('button',name='编辑',exact=True).click();panel=dialog()
                panel.get_by_role('button',name='关闭',exact=True).first.click()
                if path=='tunnel-services':
                    card.get_by_role('button',name='编辑',exact=True).click();panel=dialog()
                    panel.get_by_role('textbox',name='服务器名称',exact=True).fill('修改后的演示节点')
                    expect(panel.get_by_label('认证密码',exact=True)).to_have_value('')
                    expect(panel.get_by_label('认证 Token',exact=True)).to_have_value('')
                    state['hold_save']=True
                    before=len(server_saves)
                    panel.get_by_role('button',name='保存',exact=True).click()
                    expect(panel.get_by_role('button',name='保存中…',exact=True)).to_be_disabled()
                    expect(panel.get_by_role('button',name='关闭',exact=True)).to_have_count(0)
                    assert len(server_saves)==before+1
                    pending_saves.pop().fulfill(status=422,json=dict(detail='演示保存失败'))
                    expect(panel.get_by_role('alert')).to_contain_text('演示保存失败')
                    expect(panel.get_by_role('textbox',name='服务器名称',exact=True)).to_have_value('修改后的演示节点')
                    state['hold_save']=False
                    panel.get_by_role('button',name='保存',exact=True).click();settle()
                    expect(panel).to_have_count(0)
                if path=='api-keys':card.get_by_role('button',name='删除',exact=True).click()
                else:
                    card.get_by_role('button',name='服务器操作',exact=True).click()
                    page.get_by_role('menuitem',name='删除服务器',exact=True).click()
                cancel_confirmation()

            page.goto(demo.BASE+'/hosts');settle()
            page.get_by_role('tab',name='凭证管理',exact=True).click();settle()
            for kind in ['SSH / RDP','Docker / Portainer']:
                page.get_by_role('button',name=kind,exact=True).click();settle()
                page.get_by_role('button',name='新增凭证',exact=True).click();panel=dialog()
                panel.get_by_role('combobox',name='认证方式',exact=True).click();popup('[data-slot=select-content]')
                page.keyboard.press('Escape');panel.get_by_role('button',name='取消',exact=True).click()
                card=page.locator('article:visible').first
                card.get_by_role('button',name='编辑',exact=True).click();panel=dialog()
                assert all(field.input_value()=='' for field in panel.locator('input[type=password],textarea').all())
                panel.get_by_role('button',name='取消',exact=True).click()
                card.get_by_role('button',name='删除',exact=True).click();panel=dialog()
                panel.get_by_role('button',name='取消',exact=True).click()
            page.get_by_role('tab',name='访问授权',exact=True).click();settle()
            page.get_by_role('button',name='选择主机',exact=True).click();popup('[data-slot=combobox-content]')
            page.keyboard.press('Escape')
            page.get_by_role('button',name='撤销授权',exact=True).first.click();cancel_confirmation()
            page.get_by_role('tab',name='系统用户',exact=True).click();settle()
            page.get_by_role('button',name='证书',exact=True).first.click();dialog().get_by_role('button',name='取消',exact=True).click()
            page.get_by_role('button',name='用户菜单',exact=True).click()
            page.get_by_role('menuitem',name='用户管理',exact=True).click();dialog().get_by_role('button',name='关闭',exact=True).first.click()

            page.goto(demo.BASE+'/converter');settle()
            editor=page.locator('.cm-content').first
            editor.fill('[common]\nserver_addr=demo.example.com\nserver_port=7000')
            state['convert_fail']=True
            page.get_by_role('button',name='将 INI 转换为 TOML',exact=True).click();settle()
            expect(page.get_by_text('错误：',exact=False)).to_be_visible()
            state['convert_fail']=False
            page.get_by_role('button',name='将 INI 转换为 TOML',exact=True).click();settle()
            expect(page.locator('.cm-content').last).to_contain_text('serverAddr')
            page.get_by_role('button',name='清空输入',exact=True).click()
            expect(editor).to_have_text('')
            print(f'Mobile filters, long popups, menus, cancellation, credential dialogs, retries and conversion passed: {width}px',flush=True)
        browser.close()
    assert not errors,errors
    assert not writes,writes


if __name__=='__main__':main()
