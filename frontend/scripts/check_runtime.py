"""Runtime panel acceptance with isolated APIs; never accesses production."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlparse
from playwright.sync_api import sync_playwright, expect
import capture_screenshots as demo


def fixture():
    now = datetime.now(timezone.utc)
    stamp = lambda t: t.isoformat()
    return dict(now=stamp(now), sample_interval_seconds=60, probe_interval_seconds=300,
                sync_interval_seconds=60, retention_days=7, sample_stale=False,
                latest=dict(collected_at=stamp(now), scope='container', uptime_seconds=360000,
                    app=dict(cpu_percent=.4, cpu_cores=1, cpu_limit_cores=1, memory_used_bytes=260*1024**2,
                             memory_limit_bytes=384*1024**2, memory_percent=67.7),
                    host=dict(cpu_percent=3.2, cpu_cores=2, memory_total_bytes=1657*1024**2,
                              memory_available_bytes=578*1024**2, memory_percent=65.1, load_average=[.06, .05, .03]),
                    disk=dict(total_bytes=40*1024**3, used_bytes=20*1024**3, free_bytes=20*1024**3, percent=50),
                    rdp=dict(enabled=True, running=True, active=1, blocked_sources=3,
                             counts=dict(handshake_failures=30, rejected=2000, desktop_connected=3, native_error_lines=180))),
                vnc=dict(collected_at=stamp(now), total=2, enabled=2, needs_attention=1, connected=3, ended=2, failed=1,
                         bytes_sent=1024, bytes_received=2*1024**2, truncated=False,
                         hosts=[dict(id=9, name='演示 Mac VNC', enabled=True, ssh_name='演示 Mac SSH', issues=[], check_status='online', checked_at=stamp(now-timedelta(days=2))),
                                dict(id=10, name='待配置 Mac VNC', enabled=True, ssh_name=None, issues=['SSH 指纹尚未固定'], check_status='unknown', checked_at=None)],
                         failures=[dict(host_id=9, name='演示 Mac VNC', at=stamp(now))]),
                servers=[dict(id=1, name='演示 FRP 节点', status='success', succeeded_at=stamp(now), duration_ms=154)],
                probes=[dict(name='demo-nas_ssh', server='演示 FRP 节点', checked_at=stamp(now), status='failed',
                             message='连接被目标关闭，未收到 SSH 握手', duration_ms=39)],
                history=[dict(at=stamp(now-timedelta(minutes=30*i)), cpu_percent=(i%10)*2, memory_percent=55+i%12,
                              host_memory_percent=60+i%10, samples=30) for i in range(47, -1, -1)],
                events=[dict(server_id=1, name='demo-service_ssh', action='online', at=stamp(now-timedelta(hours=1)))])


def main():
    state = dict(data=fixture(), role='admin', fail=False, calls=0)
    errors = []
    output = Path(__file__).resolve().parents[2] / '.codex-remote-attachments' / 'runtime-acceptance'
    output.mkdir(parents=True, exist_ok=True)
    def intercept(route):
        url = urlparse(route.request.url)
        if url.netloc != '127.0.0.1:4173':
            errors.append('Unexpected external request'); route.abort(); return
        if not url.path.startswith('/api/'):
            route.continue_(); return
        if url.path == '/api/system/overview':
            state['calls'] += 1
            route.fulfill(status=503 if state['fail'] else 200,
                          json=dict(detail='测试采集服务暂不可用') if state['fail'] else state['data']); return
        if url.path == '/api/settings/user':
            route.fulfill(json=dict(username='demo-admin', role=state['role'])); return
        if url.path == '/api/builtin-frps':
            route.fulfill(json=dict(available=True, enabled=False, running=False, onboarding_seen=True)); return
        result = demo.demo_response(url)
        if result is None:
            errors.append('Missing fixture: '+url.path)
        route.fulfill(json=result or {})
    with sync_playwright() as p:
        browser = p.chromium.launch()
        context = browser.new_context(viewport=dict(width=1920, height=1080), locale='zh-CN', service_workers='block')
        context.route('**/*', intercept)
        context.add_init_script("localStorage.setItem('auth_token', btoa('demo-admin:demo-only'));localStorage.setItem('username','demo-admin')")
        page = context.new_page(); page.on('pageerror', lambda error: errors.append(str(error)))
        panel = page.get_by_role('region', name='运行维护', exact=True)
        def settle():
            page.wait_for_load_state('networkidle')
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), 'Horizontal overflow'
        for width in [1920, 390, 320]:
            page.set_viewport_size(dict(width=width, height=1080 if width > 768 else 844))
            page.goto(demo.BASE+'/dashboard'); settle()
            expect(panel).to_have_count(0)
            before = state['calls']
            page.wait_for_timeout(100)
            assert state['calls'] == before, 'Dashboard must not request runtime metrics'
            if width < 1024:
                page.get_by_role('button', name='切换导航菜单', exact=True).click()
            page.get_by_role('link', name='运行维护', exact=True).click(); settle()
            expect(panel).to_be_visible()
            expect(panel.get_by_role('tab', name='资源监控')).to_have_attribute('aria-selected', 'true')
            expect(panel.get_by_text('260.0 MiB', exact=True)).to_be_visible()
            expect(panel.get_by_text('连接被目标关闭，未收到 SSH 握手', exact=True)).not_to_be_visible()
            expect(panel.get_by_role('img', name='近24小时应用CPU、容器内存及系统内存占用峰值趋势，断线表示缺少采样')).to_have_count(1)
            page.screenshot(path=str(output/f'operations-resources-{width}.png'), full_page=True)
            before = state['calls']
            panel.get_by_role('tab', name='连接检查').click(); settle()
            expect(panel.get_by_text('连接被目标关闭，未收到 SSH 握手', exact=True)).to_be_visible()
            expect(panel.get_by_text('近期连接变化', exact=True)).to_be_visible()
            expect(panel.get_by_text('260.0 MiB', exact=True)).not_to_be_visible()
            page.screenshot(path=str(output/f'operations-connections-{width}.png'), full_page=True)
            panel.get_by_role('tab', name='连接检查').press('ArrowRight'); settle()
            expect(panel.get_by_role('tab', name='RDP 防护')).to_be_focused()
            expect(panel.get_by_text('临时限制来源', exact=True)).to_be_visible()
            assert state['calls'] == before, 'Tab switching should reuse the same snapshot'
            page.reload(); settle()
            expect(panel.get_by_role('tab', name='RDP 防护')).to_have_attribute('aria-selected', 'true')
            page.screenshot(path=str(output/f'operations-rdp-{width}.png'), full_page=True)
            panel.get_by_role('tab', name='VNC 防护').click(); settle()
            expect(panel.get_by_text('VNC 会话与防护', exact=True)).to_be_visible()
            expect(panel.get_by_text('SSH 指纹尚未固定', exact=True)).to_be_visible()
            expect(panel.get_by_text('上次检查通过', exact=False)).to_be_visible()
            expect(panel.get_by_text('2.0 MiB', exact=True)).to_be_visible()
            expect(panel.get_by_role('link', name='管理 VNC 连接')).to_have_attribute('href', '/hosts?host_type=vnc')
            expect(panel.get_by_role('link', name='演示 Mac VNC', exact=True)).to_have_attribute('href', '/hosts/9?tab=logs')
            for button in panel.get_by_role('button').all():
                if button.is_visible() and width < 768:
                    assert button.bounding_box()['height'] >= 44
            page.reload(); settle()
            expect(panel.get_by_role('tab', name='VNC 防护')).to_have_attribute('aria-selected', 'true')
            page.screenshot(path=str(output/f'operations-vnc-{width}.png'), full_page=True)
            panel.get_by_role('tab', name='VNC 防护').press('Home'); settle()
            expect(panel.get_by_role('tab', name='资源监控')).to_be_focused()
            print(f'Dashboard separation, VNC/RDP tabs, keyboard navigation and deep links: {width}px', flush=True)
        # A failed refresh keeps prior readings, clearly labelled stale.
        state['fail'] = True
        page.get_by_role('button', name='刷新运行数据').click(); settle()
        expect(panel.get_by_role('alert')).to_contain_text('读取失败')
        expect(panel.get_by_text('260.0 MiB', exact=True)).to_be_visible()
        expect(panel.get_by_text('（已过期）', exact=True)).to_be_visible()
        state['fail'] = False; state['data'] = deepcopy(fixture())
        state['data']['latest']['app'].update(cpu_percent=None, memory_used_bytes=None, memory_percent=None, memory_limit_bytes=None)
        state['data']['history'] = []; state['data']['sample_stale'] = True
        state['data']['servers'][0]['status'] = 'failed'
        page.get_by_role('button', name='刷新运行数据').click(); settle()
        expect(panel.get_by_text('等待采样', exact=True)).to_be_visible()
        expect(panel.get_by_text('未采集', exact=True).first).to_be_visible()
        panel.get_by_role('tab', name='连接检查').click(); settle()
        expect(panel.get_by_text('采集失败', exact=True)).to_be_visible()
        page.screenshot(path=str(output/'runtime-stale-mobile.png'), full_page=True)
        state['data']['latest'] = None
        page.get_by_role('button', name='刷新运行数据').click(); settle()
        expect(panel.get_by_text('正在等待首次资源采样，暂无数据。', exact=True)).to_be_visible()
        # VNC remains available before the first resource sample, with explicit empty/missing states.
        state['data']['vnc'].update(hosts=[], failures=[], total=0, enabled=0, needs_attention=0)
        page.get_by_role('button', name='刷新运行数据').click(); settle()
        panel.get_by_role('tab', name='VNC 防护').click(); settle()
        expect(panel.get_by_text('尚未添加 VNC 连接服务。', exact=True)).to_be_visible()
        state['data']['vnc'] = None
        page.get_by_role('button', name='刷新运行数据').click(); settle()
        expect(panel.get_by_text('VNC 运行数据尚不可用，请刷新重试。', exact=True)).to_be_visible()
        state['fail'] = True
        page.reload(); settle()
        expect(panel.get_by_role('alert')).to_contain_text('读取失败')
        expect(panel.get_by_text('尚未添加 VNC 连接服务。', exact=True)).to_have_count(0)
        state['fail'] = False
        # Changing routes unmounts the poller, and ordinary users never request metrics.
        state['role'] = 'user'
        before = state['calls']; page.reload(); settle()
        expect(panel).to_have_count(0)
        expect(page).to_have_url(demo.BASE+'/dashboard')
        page.get_by_role('button', name='切换导航菜单', exact=True).click()
        expect(page.get_by_role('link', name='运行维护', exact=True)).to_have_count(0)
        assert state['calls'] == before
        # Leaving the page removes its interval; even after the next tick no metrics are fetched.
        state['role'] = 'admin'; state['data'] = fixture()
        page.goto(demo.BASE+'/operations?tab=connections'); settle()
        expect(panel.get_by_role('tab', name='连接检查')).to_have_attribute('aria-selected', 'true')
        page.get_by_role('button', name='切换导航菜单', exact=True).click()
        page.get_by_role('navigation', name='主导航').get_by_role('link', name='仪表盘', exact=True).click(); settle()
        before = state['calls']; page.wait_for_timeout(31000)
        assert state['calls'] == before, 'Poller should stop after leaving operations'
        browser.close()
    assert not errors, errors
    print('Stale/failure/unknown/empty/admin-only UI checks passed', flush=True)


if __name__ == '__main__':
    main()
