"""VNC UI and real noVNC handshake against isolated demo responses only."""
import json
import re
import struct
import sys
from pathlib import Path
from urllib.parse import urlparse, parse_qs
from playwright.sync_api import sync_playwright, expect
import capture_screenshots as demo

WIDTH, HEIGHT = 640, 360
INITIAL = (struct.pack('!HH', WIDTH, HEIGHT) + bytes([32,24,0,1])
           + struct.pack('!HHH',255,255,255) + bytes([0,8,16,0,0,0])
           + struct.pack('!I',4) + b'demo')


def demo_frame(page):
    rgba = bytes(page.evaluate("""([width, height]) => {
      const canvas = document.createElement('canvas');
      canvas.width = width;
      canvas.height = height;
      const ctx = canvas.getContext('2d');
      const wallpaper = ctx.createLinearGradient(0, 0, width, height);
      wallpaper.addColorStop(0, '#1456a4');
      wallpaper.addColorStop(1, '#6d38a2');
      ctx.fillStyle = wallpaper;
      ctx.fillRect(0, 0, width, height);
      ctx.fillStyle = '#20305b';
      ctx.roundRect(146, 65, 348, 230, 18);
      ctx.fill();
      ctx.textAlign = 'center';
      ctx.fillStyle = '#fff';
      ctx.font = 'bold 38px sans-serif';
      ctx.fillText('演示桌面', 320, 130);
      ctx.font = '24px sans-serif';
      ctx.fillText('VNC 屏幕共享', 320, 174);
      ctx.fillStyle = '#e9efff';
      ctx.beginPath();
      ctx.roundRect(204, 211, 232, 48, 10);
      ctx.fill();
      ctx.fillStyle = '#20305b';
      ctx.fillText('密码输入示例', 320, 243);
      return Array.from(ctx.getImageData(0, 0, width, height).data);
    }""", [WIDTH, HEIGHT]))
    return b'\0\0\0\1' + struct.pack('!HHHHi',0,0,WIDTH,HEIGHT,0) + rgba

def main():
    state=dict(allowed=True,fail=False)
    native_url='vnc://vnc.test:15901'
    host={**demo.HOSTS[0], 'id':7,'name':'mac-vnc','host_type':'vnc','address':'127.0.0.1','port':5900,'vnc_ssh_host_id':1,'credential_id':2}
    errors=[]
    def intercept(route):
        url=urlparse(route.request.url)
        if not url.path.startswith('/api/'):
            route.continue_(); return
        if url.path == '/api/managed-hosts/7/vnc-ticket' and route.request.method == 'POST':
            route.fulfill(json=dict(username='test-ticket', password='test-only-password', expires_in=180))
            return
        if url.path == '/api/temporary-credentials/vnc/test-ticket/copy' and route.request.method == 'POST':
            route.fulfill(json=dict(username='test-ticket', password='test-only-password', address=native_url))
            return
        if route.request.method!='GET':
            errors.append('Unexpected write '+url.path); route.abort(); return
        data=demo.demo_response(url)
        if url.path=='/api/managed-hosts':
            h={**host,'permissions':['connect'] if state['allowed'] else [],'can_manage':state['allowed']}
            if parse_qs(url.query).get('host_id')==['1']: h=demo.HOSTS[0]
            data=demo.paginated([h])
        if url.path == '/api/managed-hosts/gateway/info':
            data['vnc_gateway'] = dict(running=True, port=15901)
        if url.path=='/api/managed-hosts/context': data=dict(is_admin=state['allowed'],actor_type='user',actor_name='demo')
        route.fulfill(json=data or {})
    def websocket(ws):
        stage=0
        def receive(data):
            nonlocal stage
            if stage==0:
                packet=json.loads(data)
                assert '?' not in ws.url and packet['type']=='auth'
                if state['fail']:
                    ws.send(json.dumps(dict(type='error',message='演示：连接被拒绝'))); ws.close(); return
                ws.send(json.dumps(dict(type='ready')));ws.send(b'RFB 003.008\n');stage=1
            elif stage==1:
                assert data==b'RFB 003.008\n';ws.send(b'\x01\x01');stage=2
            elif stage==2:
                assert data==b'\x01';ws.send(b'\0'*4);stage=3
            elif stage==3:
                assert data==b'\x01';ws.send(INITIAL);stage=4
                ws.send(frame)
        ws.on_message(receive)
    output=Path(__file__).resolve().parents[2]/'.codex-remote-attachments/vnc-ui';output.mkdir(parents=True,exist_ok=True)
    with sync_playwright() as p:
        browser=p.chromium.launch()
        context=browser.new_context(ignore_https_errors=True)
        context.grant_permissions(['clipboard-read','clipboard-write'],origin='https://vnc.test')
        # HTTPS origin fulfilled from local built assets, without contacting an external service.
        def asset(route):
            u=urlparse(route.request.url)
            if u.path.startswith('/api/'):intercept(route);return
            path=Path(__file__).resolve().parents[2]/'dist'/u.path.lstrip('/')
            if not path.is_file():path=Path(__file__).resolve().parents[2]/'dist/index.html'
            mime='application/javascript' if path.suffix=='.js' else 'text/css' if path.suffix=='.css' else 'text/html'
            route.fulfill(path=str(path),content_type=mime)
        context.route('**/*',asset)
        context.route_web_socket('**/api/managed-hosts/*/vnc',websocket)
        context.add_init_script("""
          // Playwright's WebSocket subclass inherits native members one level deeper.
          // noVNC enumerates own properties and the immediate prototype only.
          const p = WebSocket.prototype;
          for (const name of ['send', 'close', 'binaryType', 'bufferedAmount', 'protocol', 'readyState', 'onopen', 'onmessage', 'onerror', 'onclose']) {
            if (Object.hasOwn(p, name)) continue;
            let q = Object.getPrototypeOf(p);
            while (q && !Object.hasOwn(q, name)) q = Object.getPrototypeOf(q);
            if (q) Object.defineProperty(p, name, Object.getOwnPropertyDescriptor(q, name));
          }
        """)
        context.add_init_script("localStorage.setItem('auth_token',btoa('demo:demo-only'))")
        page=context.new_page();page.on('pageerror',lambda e:errors.append(str(e)))
        frame=demo_frame(page)
        for width in [1280,390,320]:
            page.set_viewport_size(dict(width=width,height=900))
            page.goto('https://vnc.test/dashboard')
            if width < 768: page.get_by_role('button',name='切换导航菜单',exact=True).click()
            page.get_by_role('link',name='主机资源',exact=True).click()
            page.get_by_role('button',name='连接详情',exact=True).click()
            expect(page.get_by_role('dialog')).to_contain_text(native_url)
            page.get_by_role('button',name='生成连接凭据',exact=True).click()
            expect(page.get_by_role('link',name='打开屏幕共享',exact=True)).to_have_attribute('href', native_url)
            page.get_by_role('button',name='复制临时密码',exact=True).click()
            page.wait_for_function("navigator.clipboard.readText().then(text => text === 'test-only-password')")
            page.get_by_role('button',name='复制代理地址',exact=True).click()
            assert page.evaluate('navigator.clipboard.readText()') == native_url
            page.get_by_role('button',name='复制网页链接',exact=True).click()
            assert page.evaluate('navigator.clipboard.readText()') == 'https://vnc.test/hosts/7?tab=desktop'
            expect(page.get_by_role('button',name='打开网页远程桌面',exact=True)).to_be_enabled()
            assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
            page.screenshot(path=str(output/f'vnc-details-{width}.png'))
            page.get_by_role('button',name='关闭',exact=True).click()
            expect(page.get_by_role('dialog')).to_have_count(0)
            assert not errors,errors
            page.get_by_role('button',name='远程桌面',exact=True).click()
            page.get_by_role('button',name='连接桌面',exact=True).click()
            expect(page.get_by_text('已连接',exact=True)).to_be_visible()
            expect(page.get_by_role('button',name='连接桌面',exact=True)).to_be_disabled()
            expect(page.get_by_role('button',name='断开',exact=True)).to_be_enabled()
            screen = page.get_by_label('VNC 远程桌面')
            original_height = screen.bounding_box()['height']
            page.get_by_role('button',name='最大化',exact=True).click()
            expect(page.get_by_role('button',name='还原窗口',exact=True)).to_have_attribute('aria-pressed', 'true')
            assert screen.bounding_box()['height'] > original_height
            expect(page.get_by_label('远程键盘输入')).to_be_visible()
            page.keyboard.press('Escape')
            expect(page.get_by_role('button',name='最大化',exact=True)).to_have_attribute('aria-pressed', 'false')
            assert screen.bounding_box()['height'] == original_height
            expect(page.get_by_text('已连接',exact=True)).to_be_visible()
            assert page.evaluate("(() => { const e=new Event('beforeunload',{cancelable:true}); window.dispatchEvent(e); return e.defaultPrevented; })()")
            assert page.locator('canvas').count()==1
            assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
            page.screenshot(path=str(output/f'vnc-{width}.png'))
            if width == 390 and '--docs-screenshot' in sys.argv:
                expect(page.get_by_label('远程键盘输入', exact=True)).to_be_visible()
                page.wait_for_function("""() => {
                  const canvas = document.querySelector('[aria-label="VNC 远程桌面"] canvas');
                  const pixel = canvas?.getContext('2d').getImageData(8, 8, 1, 1).data;
                  return pixel && pixel[2] - pixel[0] > 60;
                }""", timeout=10000)
                page.screenshot(path=str(demo.OUTPUT / 'vnc-mobile.png'), animations='disabled')
            page.get_by_role('tab',name='日志与流量',exact=True).click()
            expect(page.get_by_role('alertdialog')).to_be_visible()
            page.get_by_role('button',name='取消',exact=True).click()
            page.get_by_role('button',name='断开',exact=True).click()
            page.get_by_role('button',name='连接桌面',exact=True).click()
            expect(page.get_by_text('已连接',exact=True)).to_be_visible()
            assert page.locator('canvas').count()==1
            page.get_by_role('button',name='断开',exact=True).click()
            assert not page.evaluate("(() => { const e=new Event('beforeunload',{cancelable:true}); window.dispatchEvent(e); return e.defaultPrevented; })()")
            page.get_by_role('tab',name='连接信息',exact=True).click()
            page.get_by_role('link',name='编辑连接',exact=True).click()
            expect(page.get_by_label('VNC 端口',exact=True)).to_have_value('5900')
            expect(page.get_by_role('button',name='选择 SSH 隧道连接',exact=True)).to_be_visible()
            assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
            page.screenshot(path=str(output/f'vnc-editor-{width}.png'))
            page.get_by_role('button',name='SSH 主机',exact=True).click()
            expect(page.get_by_label('连接地址',exact=True)).to_have_value('')
            page.get_by_label('连接地址',exact=True).fill('preserved.example.com')
            for label,port in [('RDP 主机','3389'),('Docker 主机','9443'),('SSH 主机','22')]:
                page.get_by_role('button',name=label,exact=True).click()
                expect(page.get_by_label('连接地址',exact=True)).to_have_value('preserved.example.com')
                expect(page.get_by_label('SSH 端口' if label=='SSH 主机' else '端口',exact=True)).to_have_value(port)
            page.get_by_role('button',name='VNC 主机',exact=True).click()
            expect(page.get_by_label('VNC 地址',exact=True)).to_have_value('preserved.example.com')
            expect(page.get_by_label('选择 SSH 隧道连接',exact=True)).to_have_count(0)
            expect(page.get_by_label('VNC 端口',exact=True)).to_have_value('5900')
            page.get_by_role('button',name='取消',exact=True).first.click()
            expect(page.get_by_role('alertdialog')).to_contain_text('尚未保存')
            page.get_by_role('button',name='放弃修改',exact=True).click()
            expect(page).to_have_url(re.compile('/hosts'))
            print(f'VNC desktop, noVNC handshake, SPA tabs and leave protection: {width}px',flush=True)
        state['fail']=True
        page.goto('https://vnc.test/hosts/7?tab=desktop')
        page.get_by_role('button',name='连接桌面',exact=True).click()
        expect(page.get_by_role('alert')).to_contain_text('连接被拒绝')
        state['allowed']=False
        page.goto('https://vnc.test/hosts/7?tab=desktop')
        expect(page.get_by_role('tab',name='远程桌面',exact=True)).to_have_count(0)
        page.get_by_role('link',name='← 返回连接列表',exact=True).click()
        expect(page.get_by_role('button',name='远程桌面',exact=True)).to_have_count(0)
        page.get_by_role('button',name='连接详情',exact=True).click()
        expect(page.get_by_role('button',name='打开网页远程桌面',exact=True)).to_be_disabled()
        expect(page.get_by_role('button',name='复制 Mac 屏幕共享地址',exact=True)).to_have_count(0)
        assert not errors,errors
        browser.close()
    print('VNC failure and ordinary-user permissions passed',flush=True)

if __name__=='__main__':main()
