"""Read-only acceptance matrix for every mobile page, tab, and shared control."""
from pathlib import Path
from urllib.parse import urlparse
import json
import sys
from playwright.sync_api import sync_playwright, expect
import capture_screenshots as demo
from check_runtime import fixture

OUT=Path(__file__).resolve().parents[2]/'.codex-remote-attachments/mobile-pages'


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    demo.RESPONSES['/api/system/overview']=fixture()
    if '--long' in sys.argv:
        for rows, fields in [(demo.SERVERS,['name','server_addr','api_base_url','server_version']),
                (demo.PACKAGES,['filename','platform','version']), (demo.KEYS,['description']),
                (demo.SSH_CREDENTIALS,['name','username']), (demo.DOCKER_CREDENTIALS,['name']),
                (demo.SUBJECTS,['name']), (demo.AUDIT,['host_name','actor_name','command','target'])]:
            for row in rows:
                for field in fields:row[field]=str(row.get(field) or '')+'超长内容long-value-'*24
        for row in demo.GRANTS:
            row['host_name']+='host-long-value-'*30
            row['subject_name']+='subject-long-value-'*30
    issues, errors, checked=[],[],[]
    def intercept(route):
        u=urlparse(route.request.url)
        if u.netloc!='127.0.0.1:4173': errors.append('External '+u.netloc);route.abort();return
        if not u.path.startswith('/api/'):route.continue_();return
        if u.path=='/api/builtin-frps/raw-config/preview' and route.request.method=='POST':
            route.fulfill(json=dict(content='bindPort = 7000\n',revision='demo',changed=False));return
        data=demo.demo_response(u)
        if route.request.method!='GET' or data is None:
            errors.append(route.request.method+' '+u.path);route.fulfill(status=501,json={});return
        route.fulfill(json=data)
    with sync_playwright() as p:
        browser=p.chromium.launch()
        ctx=browser.new_context(reduced_motion='reduce',locale='zh-CN',has_touch=True,is_mobile=True)
        ctx.route('**/*',intercept)
        ctx.add_init_script("localStorage.setItem('auth_token',btoa('demo-admin:demo-only'));localStorage.setItem('currentServerId','1')")
        page=ctx.new_page();page.on('pageerror',lambda e:errors.append(str(e)))
        def check(name,width):
            page.wait_for_load_state('networkidle')
            expect(page.locator('main h1')).to_have_count(1)
            result=page.evaluate('''()=>{
              const visible=el=>el.getClientRects().length && getComputedStyle(el).visibility!=='hidden';
              const label=el=>el.getAttribute('aria-label')||el.textContent.trim().slice(0,45)||el.getAttribute('placeholder')||el.tagName;
              const small=[...document.querySelectorAll('main button,main input,main [role="tab"],header button')].filter(visible).filter(el=>{
                if(el.closest('.cm-editor'))return false;
                const hit=el.matches('[role="checkbox"],input[type="checkbox"],input[type="radio"]')?el.closest('label')||el:el;
                const b=hit.getBoundingClientRect();
                if(el.matches('[role="checkbox"]')){const after=getComputedStyle(el,'::after');const r=el.getBoundingClientRect();if(r.width-parseFloat(after.left)-parseFloat(after.right)>=44 && r.height-parseFloat(after.top)-parseFloat(after.bottom)>=44)return false;}
                return b.height<43.5 || (b.width<43.5 && el.matches('button,[role="tab"]'));
              }).map(el=>({label:label(el),slot:el.dataset.slot,h:el.getBoundingClientRect().height,w:el.getBoundingClientRect().width}));
              const fields=[...document.querySelectorAll('main input,main textarea,main [data-slot="select-trigger"]')].filter(visible).filter(el=>!el.closest('.cm-editor') && !el.matches('[type="checkbox"],[type="radio"],[type="file"]') && parseFloat(getComputedStyle(el).fontSize)<16).map(label);
              const cards=[...document.querySelectorAll('main article,main .mobile-record,main li[data-group-name]')].filter(visible).filter(el=>el.scrollWidth>el.clientWidth+1 || el.scrollHeight>el.clientHeight+1).map(label);
              const buttonText=[...document.querySelectorAll('main button,header button')].filter(visible).filter(el=>el.innerText.trim() && (el.scrollWidth>el.clientWidth+1 || el.scrollHeight>el.clientHeight+1)).map(label);
              return {overflow:document.documentElement.scrollWidth>innerWidth,small,fields,cards,buttonText};
            }''')
            if any(result.values()):issues.append(dict(page=name,width=width,**result))
            checked.append(dict(page=name,width=width))
            if width==390:page.screenshot(path=str(OUT/(name.replace('/','-')+('-long' if '--long' in sys.argv else '')+'.png')),full_page=True)
        def navigate(label):
            toggle=page.get_by_role('button',name='切换导航菜单',exact=True)
            mobile=toggle.is_visible()
            if mobile:toggle.click()
            link=page.get_by_role('navigation',name='主导航').get_by_role('link',name=label,exact=True)
            target=link.get_attribute('href')
            link.click()
            expect(page).to_have_url(demo.BASE+target)
            if mobile:expect(page.get_by_role('navigation',name='主导航')).not_to_be_visible()
        routes=[('仪表盘','dashboard'),('运行维护','operations'),('代理列表','proxies'),('分组管理','groups'),('穿透服务','tunnel-services'),('主机资源','hosts'),('安装包管理','packages'),('配置转换','converter'),('密钥管理','api-keys')]
        for width in ([844] if '--landscape' in sys.argv else [320,390,430]):
            page.set_viewport_size(dict(width=width,height=390 if width==844 else 844))
            page.goto(demo.BASE+'/dashboard');check('dashboard',width)
            for label,path in routes[1:]:
                navigate(label);check(path,width)
                if path=='operations':
                    for tab in ['连接检查','RDP 防护','资源监控']:
                        page.get_by_role('tab',name=tab,exact=True).click();check('operations/'+tab,width)
                if path=='tunnel-services':
                    page.get_by_role('tab',name='内置服务',exact=True).click();check('tunnel-services/builtin',width)
                    for tab in ['安全设置','插件','原始配置文件','基础配置']:
                        page.get_by_role('tab',name=tab,exact=True).click()
                        if tab=='插件':page.get_by_role('button',name='添加插件',exact=True).click()
                        check('tunnel-services/'+tab,width)
                    page.get_by_role('tab',name='服务节点',exact=True).click()
                if path=='hosts':
                    for tab in ['凭证管理','访问授权','系统用户','审计与流量','API 访问','主机列表']:
                        page.get_by_role('tab',name=tab,exact=True).click();check('hosts/'+tab,width)
                        if tab=='凭证管理':
                            page.get_by_role('button',name='Docker / Portainer',exact=True).click();check('hosts/Docker凭证',width)
                if path=='converter':
                    page.get_by_role('tab',name='命令行工具',exact=True).click();check('converter/command',width)
            for path in ['hosts/new','hosts/1/edit','hosts/2/edit','hosts/3/edit','hosts/1','hosts/1?tab=logs','hosts/1?tab=terminal']:
                page.goto(demo.BASE+'/'+path);check(path.replace('?','-'),width)
            print(f'Mobile page and tab matrix inspected: {width}px',flush=True)
        browser.close()
    (OUT/('result'+('-landscape' if '--landscape' in sys.argv else '')+('-long' if '--long' in sys.argv else '')+'.json')).write_text(json.dumps(dict(checked=checked,issues=issues,errors=errors),ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(dict(views=len(checked),issues=issues,errors=errors),ensure_ascii=False),flush=True)
    assert not errors,errors
    assert not issues,issues


if __name__=='__main__':main()


