"""Real browser -> disposable HTTPS app -> real SSH fingerprint -> VNC creation.

Run with the backend dependencies and Playwright installed; no production access.
--reproduce demonstrates the original missing-fingerprint dead end.
"""
import base64
import json
import os
import re
from pathlib import Path
import secrets
import subprocess
import sys
import tempfile
import time

import httpx
from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'backend'))
sys.path.insert(0, str(ROOT / 'backend/scripts'))
from check_vnc_live import DesktopFixture, certificate, listen


def main():
    reproduce = '--reproduce' in sys.argv
    output = ROOT / '.codex-remote-attachments/vnc-onboarding'
    output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='vnc-onboarding-') as temporary:
        folder = Path(temporary); certificate(folder)
        password = secrets.token_hex(16)
        env = {**os.environ, 'DATABASE_URL': 'sqlite:///'+str(folder/'test.db'),
               'AUTH_USERNAME': 'onboarding-admin', 'AUTH_PASSWORD': password,
               'SSH_CREDENTIAL_SECRET': secrets.token_hex(32), 'BUILTIN_FRPS_ENABLED': 'false',
               'SSH_GATEWAY_ENABLED': 'false', 'DOCKER_GATEWAY_ENABLED': 'false', 'RDP_GATEWAY_ENABLED': 'false',
               'PYTHONPATH': str(ROOT/'backend')}
        os.environ.update(env)
        fixture = DesktopFixture()
        sock = listen(); port = sock.getsockname()[1]; sock.close()
        base = f'https://127.0.0.1:{port}'
        with (folder/'server.log').open('w') as log:
            server = subprocess.Popen([sys.executable, '-m', 'uvicorn', 'app.main:app', '--host', '127.0.0.1', '--port', str(port),
                                       '--ssl-keyfile', str(folder/'key.pem'), '--ssl-certfile', str(folder/'cert.pem')],
                                      cwd=ROOT/'backend', env=env, stdout=log, stderr=log)
            try:
                client = httpx.Client(base_url=base, auth=(env['AUTH_USERNAME'],password), verify=str(folder/'cert.pem'), trust_env=False, timeout=25)
                for _ in range(120):
                    try:
                        if client.get('/api/public/version').is_success: break
                    except httpx.HTTPError: pass
                    assert server.poll() is None, 'Disposable app exited'
                    time.sleep(.25)
                else: raise AssertionError('Disposable app failed to start')
                def api(method, path, **kwargs):
                    result = client.request(method, '/api/'+path, **kwargs)
                    assert result.is_success, (path,result.status_code)
                    return result.json()
                api('POST','builtin-frps/onboarding-seen')
                ssh = api('POST','ssh-credentials',json=dict(name='Mac SSH credential',username='fixture',auth_type='password',password=fixture.ssh_password))
                vnc = api('POST','ssh-credentials',json=dict(name='VNC credential',username='vnc',auth_type='password',password=fixture.password))
                with sync_playwright() as p:
                    browser = p.chromium.launch()
                    for width in ([1280] if reproduce else [1280,390,320]):
                        errors = []
                        context = browser.new_context(ignore_https_errors=True, viewport=dict(width=width,height=900), reduced_motion='reduce')
                        def route(request):
                            from urllib.parse import urlparse
                            url = urlparse(request.request.url)
                            assert url.netloc == f'127.0.0.1:{port}', 'Unexpected external request'
                            if url.path.startswith('/api/'):
                                request.continue_(); return
                            path = ROOT/'dist'/url.path.lstrip('/')
                            if not path.is_file(): path = ROOT/'dist/index.html'
                            mime = 'application/javascript' if path.suffix == '.js' else 'text/css' if path.suffix == '.css' else 'text/html'
                            request.fulfill(path=str(path),content_type=mime)
                        context.route('**/*',route)
                        token = base64.b64encode(f"{env['AUTH_USERNAME']}:{password}".encode()).decode()
                        context.add_init_script(f"localStorage.setItem('auth_token',{json.dumps(token)})")
                        page = context.new_page(); page.set_default_timeout(10000); page.on('pageerror',lambda e: errors.append(str(e)))
                        page.goto(base+'/dashboard')
                        if width < 1024: page.get_by_role('button',name='切换导航菜单',exact=True).click()
                        page.get_by_role('link',name='主机资源',exact=True).click()
                        page.get_by_role('button',name='添加主机',exact=True).click()
                        name = f'Mac SSH {width}'
                        page.get_by_label('主机名称',exact=True).fill(name)
                        page.get_by_label('连接地址',exact=True).fill('127.0.0.1')
                        page.get_by_label('端口',exact=True).fill(str(fixture.ssh.getsockname()[1]))
                        page.get_by_label('选择凭据',exact=True).click()
                        page.get_by_role('option',name='Mac SSH credential (fixture)',exact=True).click()
                        expect(page.get_by_placeholder('SHA256:...',exact=True)).to_have_value('')
                        page.get_by_role('button',name='保存主机',exact=True).first.click()
                        expect(page).to_have_url(re.compile(re.escape(base)+r'/hosts(?:\?.*)?$'))
                        host = next(h for h in api('GET','managed-hosts',params=dict(page=1,page_size=100))['items'] if h['name']==name)
                        assert not host['host_key_fingerprint']
                        page.get_by_role('button',name='添加主机',exact=True).click()
                        page.get_by_role('button',name='VNC 主机',exact=True).click()
                        page.get_by_label('主机名称',exact=True).fill(f'Mac VNC {width}')
                        page.get_by_label('端口',exact=True).fill(str(fixture.rfb.getsockname()[1]))
                        page.get_by_label('选择已核验指纹的 Mac SSH 主机',exact=True).click()
                        page.get_by_role('option',name=name,exact=True).click()
                        page.get_by_label('选择凭据',exact=True).click()
                        page.get_by_role('option',name='VNC credential (vnc)',exact=True).click()
                        with page.expect_response(lambda r: r.request.method=='POST' and r.url==base+'/api/managed-hosts') as result:
                            page.get_by_role('button',name='保存主机',exact=True).first.click()
                        assert result.value.status==409
                        expect(page.get_by_role('alert')).to_contain_text('SSH 指纹')
                        if reproduce:
                            assert page.get_by_role('button',name='检测并记录 SSH 指纹',exact=True).count()==0
                            page.screenshot(path=str(output/'before-blocked.png'),full_page=True)
                            print('Reproduced: blank-fingerprint SSH saves, but VNC creation returns 409 with no inline detection',flush=True)
                            context.close(); break
                        if width == 1280:
                            api('PUT',f"ssh-credentials/{ssh['id']}",json=dict(password='deliberately-wrong'))
                            page.get_by_role('button',name='检测并记录 SSH 指纹',exact=True).click()
                            expect(page.get_by_role('alert')).to_contain_text('主机连接失败',timeout=30000)
                            assert not api('GET','managed-hosts',params=dict(page=1,host_id=host['id']))['items'][0]['host_key_fingerprint']
                            api('PUT',f"ssh-credentials/{ssh['id']}",json=dict(password=fixture.ssh_password))
                        page.get_by_role('button',name='检测并记录 SSH 指纹',exact=True).click()
                        expect(page.get_by_text('SSH 检测通过，可保存 VNC 主机。',exact=True)).to_be_visible(timeout=30000)
                        from app.services.ssh_client import format_host_key_fingerprint
                        pinned = api('GET','managed-hosts',params=dict(page=1,host_id=host['id']))['items'][0]
                        assert pinned['host_key_fingerprint']==format_host_key_fingerprint(fixture.key)
                        if width == 1280:
                            api('PUT',f"managed-hosts/{host['id']}",json=dict(host_key_fingerprint='SHA256:wrong'))
                            page.get_by_role('button',name='重新检测 SSH',exact=True).click()
                            expect(page.get_by_role('alert')).to_contain_text('指纹不匹配',timeout=30000)
                            assert api('GET','managed-hosts',params=dict(page=1,host_id=host['id']))['items'][0]['host_key_fingerprint']=='SHA256:wrong'
                            api('PUT',f"managed-hosts/{host['id']}",json=dict(host_key_fingerprint=pinned['host_key_fingerprint']))
                            page.get_by_role('button',name='重新检测 SSH',exact=True).click()
                            expect(page.get_by_text('SSH 检测通过，可保存 VNC 主机。',exact=True)).to_be_visible(timeout=30000)
                        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
                        page.screenshot(path=str(output/f'after-ready-{width}.png'),full_page=True)
                        page.get_by_role('button',name='保存主机',exact=True).first.click()
                        expect(page).to_have_url(re.compile(re.escape(base)+r'/hosts(?:\?.*)?$'))
                        created = next(h for h in api('GET','managed-hosts',params=dict(page=1,page_size=100))['items'] if h['name']==f'Mac VNC {width}')
                        assert created['vnc_ssh_host_id']==host['id']
                        assert api('POST',f"managed-hosts/{created['id']}/test")['success']
                        assert not errors, errors
                        context.close()
                        print(f'Real SPA create SSH without manual fingerprint -> inline SSH test -> save and test VNC: {width}px',flush=True)
                    browser.close()
            finally:
                server.terminate()
                try: server.wait(timeout=5)
                except subprocess.TimeoutExpired: server.kill(); server.wait()
                fixture.ssh.close(); fixture.rfb.close()


if __name__ == '__main__': main()
