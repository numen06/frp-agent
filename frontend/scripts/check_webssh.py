"""Exercise real xterm rendering/input over isolated WebSocket demo messages."""
import json
from pathlib import Path
from urllib.parse import urlparse
from playwright.sync_api import sync_playwright, expect
import capture_screenshots as demo


def main():
    errors, packets, urls = [], [], []
    state = dict(fail=False, execute=True)
    output = Path(__file__).resolve().parents[2]/'.codex-remote-attachments/usability'
    output.mkdir(parents=True,exist_ok=True)

    def intercept(route):
        u=urlparse(route.request.url)
        if u.netloc!='127.0.0.1:4173':
            errors.append('Unexpected external request'); route.abort(); return
        if not u.path.startswith('/api/'): route.continue_(); return
        if route.request.method!='GET':
            errors.append('Unexpected mutation: '+u.path); route.fulfill(status=500,json={}); return
        data=demo.demo_response(u)
        if u.path=='/api/managed-hosts' and not state['execute']:
            data={**data,'items':[{**h,'permissions':['connect']} for h in data['items']]}
        if data is None: errors.append('Missing fixture: '+u.path)
        route.fulfill(json=data or {})

    def websocket(ws):
        urls.append(ws.url)
        assert '?' not in ws.url and 'demo-only' not in ws.url
        def receive(raw):
            packet=json.loads(raw); packets.append(packet)
            if packet['type']=='auth':
                assert packet['authorization'].startswith('Basic ')
                if state['fail']:
                    ws.send(json.dumps(dict(type='error',message='SSH 主机指纹不匹配，连接已阻止')))
                    ws.close(code=1008,reason='demo mismatch'); return
                ws.send(json.dumps(dict(type='ready')))
                ws.send(b'\x1b[32mWeb SSH demo ready\x1b[0m\r\n$ ')
            elif packet['type']=='input': ws.send(packet['data'].encode())
        ws.on_message(receive)

    with sync_playwright() as p:
        browser=p.chromium.launch()
        context=browser.new_context(locale='zh-CN',reduced_motion='reduce')
        context.route('**/*',intercept)
        context.route_web_socket('**/api/managed-hosts/*/terminal',websocket)
        context.add_init_script("localStorage.setItem('auth_token',btoa('demo-admin:demo-only'))")
        page=context.new_page();page.on('pageerror',lambda e:errors.append(str(e)))
        for width in [1280,390,320]:
            page.set_viewport_size(dict(width=width,height=900))
            page.goto(demo.BASE+'/hosts');page.wait_for_load_state('networkidle')
            card=page.locator('article').filter(has=page.get_by_role('heading',name='production-linux',exact=True))
            card.get_by_role('button',name='Web SSH',exact=True).click()
            expect(page.get_by_role('tab',name='Web SSH',exact=True)).to_have_attribute('aria-selected','true')
            expect(page.get_by_text('已连接',exact=True)).to_be_visible()
            expect(page.locator('.xterm-screen')).to_contain_text('Web SSH demo ready')
            page.keyboard.type('echo webssh-check');page.keyboard.press('Enter')
            page.get_by_role('button',name='Ctrl+C',exact=True).click()
            page.get_by_role('button',name='Tab',exact=True).click()
            expect(page.get_by_role('region',name='SSH 交互终端',exact=True)).to_be_visible()
            page.wait_for_timeout(80)
            assert 'echo webssh-check' in ''.join(p.get('data','') for p in packets)
            assert any(p.get('data')=='\x03' for p in packets)
            assert any(p.get('data')=='\t' for p in packets)
            assert any(p['type']=='resize' and p['cols']>0 and p['rows']>0 for p in packets)
            assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
            page.screenshot(path=str(output/f'webssh-{width}.png'))
            page.get_by_role('tab',name='日志与流量',exact=True).click()
            expect(page.get_by_role('alertdialog')).to_contain_text('断开当前 SSH 会话')
            page.get_by_role('button',name='取消',exact=True).click()
            expect(page.get_by_text('已连接',exact=True)).to_be_visible()
            page.get_by_role('button',name='断开',exact=True).click()
            expect(page.get_by_text('已断开',exact=True)).to_be_visible()
            page.get_by_role('tab',name='日志与流量',exact=True).click()
            expect(page.get_by_role('alertdialog')).to_have_count(0)
            print(f'Web SSH input/control/resize/leave protection passed: {width}px',flush=True)
        state['fail']=True
        page.goto(demo.BASE+'/hosts/1?tab=terminal')
        expect(page.get_by_role('alert')).to_contain_text('指纹不匹配')
        state['fail']=False
        page.get_by_role('button',name='重新连接',exact=True).click()
        expect(page.get_by_text('已连接',exact=True)).to_be_visible()
        page.get_by_role('tab',name='主机信息',exact=True).click()
        page.get_by_role('button',name='断开并离开',exact=True).click()
        expect(page.get_by_role('tab',name='主机信息',exact=True)).to_have_attribute('aria-selected','true')
        expect(page.get_by_role('region',name='SSH 交互终端',exact=True)).to_have_count(0)
        before=len(urls);state['execute']=False
        page.goto(demo.BASE+'/hosts/1?tab=terminal');page.wait_for_load_state('networkidle')
        expect(page.get_by_role('tab',name='Web SSH',exact=True)).to_have_count(0)
        assert len(urls)==before,'Connect-only permission must never open a WebSocket'
        browser.close()
    assert not errors, errors
    print('Real xterm rendering, authenticated WS messages, reconnect, cleanup and execute permission passed.',flush=True)


if __name__=='__main__':main()
