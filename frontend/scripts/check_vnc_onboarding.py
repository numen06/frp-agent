"""Real browser -> disposable HTTPS app -> real SSH fingerprint -> VNC creation.

Run with the backend dependencies and Playwright installed; no production access.
Covers group -> machine -> independent protocols, direct VNC and optional SSH.
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
                node = api('POST','servers',json=dict(name='onboarding-node',server_addr='127.0.0.1',server_port=1,api_base_url='http://127.0.0.1:1',auth_username='fixture',auth_password='fixture',is_active=False))
                api('POST','groups/create',json=dict(frps_server_id=node['id'],group_name='lab',create_defaults=False))
                failures = {'machines': False}
                with sync_playwright() as p:
                    browser = p.chromium.launch()
                    def route(request):
                        from urllib.parse import urlparse
                        url = urlparse(request.request.url)
                        assert url.netloc == f'127.0.0.1:{port}', 'Unexpected external request'
                        if url.path.startswith('/api/'):
                            if failures['machines'] and url.path == '/api/host-machines':
                                request.fulfill(status=503,json=dict(detail='隔离测试：主机列表读取失败')); return
                            request.continue_(); return
                        path = ROOT/'dist'/url.path.lstrip('/')
                        if not path.is_file(): path = ROOT/'dist/index.html'
                        mime = 'application/javascript' if path.suffix == '.js' else 'text/css' if path.suffix == '.css' else 'text/html'
                        request.fulfill(path=str(path),content_type=mime)
                    def context_for(username, secret, width):
                        context = browser.new_context(ignore_https_errors=True, viewport=dict(width=width,height=900), reduced_motion='reduce')
                        context.route('**/*',route)
                        # Fulfilled test assets have no network address classification in Chromium.
                        context.grant_permissions(['local-network-access'],origin=base)
                        token = base64.b64encode(f'{username}:{secret}'.encode()).decode()
                        context.add_init_script(f"localStorage.setItem('auth_token',{json.dumps(token)})")
                        return context
                    for width in [1280,390,320]:
                        errors = []
                        context = context_for(env['AUTH_USERNAME'],password,width)
                        page = context.new_page(); page.set_default_timeout(12000); page.on('pageerror',lambda e: errors.append(str(e))); page.on('console',lambda msg: print('Browser diagnostic: '+msg.text,flush=True) if msg.type=='error' else None)
                        try:
                            page.goto(base+'/dashboard')
                            if width < 1024: page.get_by_role('button',name='切换导航菜单',exact=True).click()
                            page.get_by_role('link',name='主机资源',exact=True).click()
                            page.get_by_role('link',name='添加主机',exact=True).click()
                            name = f'Mac {width}'
                            page.get_by_label('主机名称',exact=True).fill(name)
                            page.get_by_label('选择分组（可选）',exact=True).click()
                            page.get_by_role('option',name='onboarding-node / lab',exact=True).click()
                            page.get_by_role('button',name='保存主机',exact=True).click()
                            expect(page.locator('main h1')).to_have_text(name)
                            machine = next(row for row in api('GET','host-machines',params=dict(page=1,page_size=100))['items'] if row['name']==name)
                            page.get_by_role('link',name='添加连接服务',exact=True).click()
                            page.get_by_role('button',name='VNC 主机',exact=True).click()
                            expect(page.get_by_label('连接名称',exact=True)).to_have_value(name+'-vnc')
                            expect(page.get_by_label('VNC 端口',exact=True)).to_have_value('5900')
                            expect(page.get_by_label('选择 SSH 隧道连接',exact=True)).to_have_count(0)
                            expect(page.get_by_placeholder('SHA256:...',exact=True)).to_have_count(0)
                            page.get_by_label('VNC 地址',exact=True).fill('127.0.0.1')
                            page.get_by_label('VNC 端口',exact=True).fill(str(fixture.rfb.getsockname()[1]))
                            page.get_by_label('选择凭据',exact=True).click()
                            page.get_by_role('option',name='VNC credential (vnc)',exact=True).click()
                            page.get_by_role('button',name='保存连接服务',exact=True).first.click()
                            expect(page).to_have_url(base+f"/machines/{machine['id']}")
                            services = api('GET','managed-hosts',params=dict(page=1,machine_id=machine['id']))['items']
                            assert len(services)==1 and services[0]['host_type']=='vnc' and services[0]['vnc_ssh_host_id'] is None
                            desktop = services[0]
                            assert api('POST',f"managed-hosts/{desktop['id']}/test")['success']
                            page.get_by_role('link',name='远程桌面',exact=True).click()
                            page.get_by_role('button',name='连接桌面',exact=True).click()
                            expect(page.get_by_text('已连接',exact=True)).to_be_visible(timeout=30000)
                            assert page.locator('canvas').count()==1
                            assert fixture.password not in page.evaluate('JSON.stringify(localStorage)')
                            page.get_by_role('button',name='断开',exact=True).click()
                            page.get_by_role('link',name='← 返回所属主机',exact=True).click()
                            page.get_by_role('link',name='添加连接服务',exact=True).click()
                            page.get_by_label('连接地址',exact=True).fill('127.0.0.1')
                            page.get_by_label('SSH 端口',exact=True).fill(str(fixture.ssh.getsockname()[1]))
                            page.get_by_label('选择凭据',exact=True).click()
                            page.get_by_role('option',name='Mac SSH credential (fixture)',exact=True).click()
                            page.get_by_role('button',name='保存连接服务',exact=True).first.click()
                            expect(page).to_have_url(base+f"/machines/{machine['id']}")
                            services = api('GET','managed-hosts',params=dict(page=1,machine_id=machine['id']))['items']
                            assert {row['host_type'] for row in services}=={'ssh','vnc'}
                            shell = next(row for row in services if row['host_type']=='ssh')
                            assert api('POST',f"managed-hosts/{shell['id']}/test")['success']
                            assert not next(row for row in services if row['host_type']=='vnc')['vnc_ssh_host_id']
                            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
                            page.wait_for_load_state('networkidle')
                            expect(page.get_by_text('SSH · '+shell['name'],exact=True)).to_be_visible()
                            expect(page.get_by_text('VNC · '+desktop['name'],exact=True)).to_be_visible()
                            page.mouse.move(0,899)
                            expect(page.get_by_role('button',name='Close toast')).to_have_count(0,timeout=15000)
                            page.screenshot(path=str(output/f'machine-services-{width}.png'),full_page=True)
                            page.locator(f"a[href^='/hosts/{desktop['id']}/edit?']").click()
                            page.get_by_label('使用 SSH 隧道（可选）',exact=True).click()
                            page.get_by_label('选择 SSH 隧道连接',exact=True).click()
                            page.get_by_role('option',name=shell['name'],exact=True).click()
                            expect(page.get_by_text(f"SSH 地址：127.0.0.1 · SSH 端口：{shell['port']}",exact=True)).to_be_visible()
                            expect(page.get_by_label('VNC 端口',exact=True)).to_have_value(str(desktop['port']))
                            page.get_by_role('button',name='保存连接服务',exact=True).first.click()
                            expect(page).to_have_url(base+f"/machines/{machine['id']}")
                            assert api('POST',f"managed-hosts/{desktop['id']}/test")['success']
                            assert not errors, errors
                            print(f'Group -> one machine -> independent VNC first and SSH later, real WSS desktop, optional SSH ports: {width}px',flush=True)
                        except Exception:
                            page.screenshot(path=str(output/'failure.png'),full_page=True)
                            (output/'failure-dom.txt').write_text(page.locator('body').inner_text())
                            raise
                        finally:
                            context.close()
                    # Only the explicitly granted VNC service is exposed, even on a shared machine.
                    username='vnc-only'; secret=secrets.token_hex(16)
                    operator=api('POST','managed-hosts/access/users',json=dict(username=username,password=secret,role='user'))
                    api('POST','managed-hosts/access/grants',json=dict(host_id=desktop['id'],subject_type='user',subject_id=operator['id'],can_connect=True))
                    context=context_for(username,secret,390); page=context.new_page()
                    page.goto(base+f"/machines/{machine['id']}")
                    expect(page.get_by_text('VNC · '+desktop['name'],exact=True)).to_be_visible()
                    expect(page.get_by_text('SSH · '+shell['name'],exact=True)).to_have_count(0)
                    expect(page.get_by_role('link',name='添加连接服务',exact=True)).to_have_count(0)
                    page.screenshot(path=str(output/'machine-user-390.png'),full_page=True)
                    context.close()
                    context=context_for(env['AUTH_USERNAME'],password,390); page=context.new_page()
                    failures['machines']=True;page.goto(base+'/machines')
                    expect(page.get_by_role('alert')).to_contain_text('主机列表读取失败')
                    expect(page.get_by_text('暂无可见主机',exact=False)).to_have_count(0)
                    failures['machines']=False;page.get_by_role('button',name='重试读取',exact=True).click()
                    expect(page.get_by_role('link',name='Mac 320',exact=True)).to_be_visible()
                    page.get_by_role('link',name='添加主机',exact=True).click()
                    page.get_by_label('主机名称',exact=True).fill('unsaved')
                    page.get_by_role('link',name='取消',exact=True).click()
                    expect(page.get_by_role('alertdialog')).to_be_visible()
                    page.get_by_role('button',name='放弃修改',exact=True).click()
                    context.close(); browser.close()
                    print('Ordinary-user service isolation, failed-read retry and unsaved machine leave guard passed',flush=True)
            finally:
                server.terminate()
                try: server.wait(timeout=5)
                except subprocess.TimeoutExpired: server.kill(); server.wait()
                log.flush(); (output/'backend.log').write_text((folder/'server.log').read_text())
                fixture.ssh.close(); fixture.rfb.close()


if __name__ == '__main__': main()
