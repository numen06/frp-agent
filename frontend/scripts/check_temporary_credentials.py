"""Run after npm run build with Playwright installed."""
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlparse

from playwright.sync_api import expect, sync_playwright

from capture_screenshots import demo_response

ORIGIN = "https://credentials.test"
DIST = Path(__file__).resolve().parents[2] / "dist"
EXPIRY = (datetime.now(timezone.utc) + timedelta(minutes=5)).isoformat()
RDP = dict(protocol="rdp", username="rdp-0123456789abcdef01234567#", owner="demo-admin",
           target="测试 Windows", address="rdp.example.test:13389", host_id=3, expires_at=EXPIRY,
           status="active", uses=0, can_copy=True)
VNC = dict(RDP, protocol="vnc", username="test-vnc", target="测试 Mac",
           address="vnc://vnc.example.test:15901", host_id=9)
OTHER = dict(RDP, username="other-rdp", target="其他签发人", owner="other", can_copy=False)
PASSWORD = "test-only-password"
RDP_FILE = f"full address:s:{RDP['address']}\r\nusername:s:{RDP['username']}\r\n".encode("utf-16")
state = dict(admin=True, certificate=True, copies=0, downloads=0)


def serve(route):
    url = urlparse(route.request.url)
    path = url.path
    if path == "/api/temporary-credentials":
        rows = [RDP, VNC] + ([OTHER] if state["admin"] else [])
        route.fulfill(json=dict(items=rows, total=len(rows), page=1, page_size=20))
    elif path.startswith("/api/temporary-credentials/") and path.endswith("/copy"):
        state["copies"] += 1
        row = RDP if "/rdp/" in path else VNC
        assert ("%23" in path if row is RDP else "/test-vnc/" in path)
        route.fulfill(json={**row, "password": PASSWORD})
    elif path == "/api/managed-hosts/3/test":
        route.fulfill(json=dict(success=state["certificate"], stderr="证书指纹不匹配"))
    elif path == "/api/managed-hosts/3/rdp-file":
        state["downloads"] += 1
        assert route.request.post_data_json == {"ticket_username": RDP["username"]}
        route.fulfill(body=RDP_FILE, content_type="application/x-rdp")
    elif path == "/api/managed-hosts/3/rdp-ticket":
        route.fulfill(status=201, json={**RDP, "password": PASSWORD})
    elif path == "/api/managed-hosts/context":
        route.fulfill(json=dict(is_admin=state["admin"], actor_type="user", actor_name="demo-admin"))
    elif path == "/api/settings/user":
        route.fulfill(json=dict(username="demo-admin", role="admin" if state["admin"] else "user"))
    elif path.startswith("/api/"):
        data = demo_response(url)
        route.fulfill(json=data if data is not None else {})
    else:
        asset = DIST / path.lstrip("/")
        if not asset.is_file():
            asset = DIST / "index.html"
        route.fulfill(path=str(asset))


def clipboard(page, expected):
    page.wait_for_function("value => navigator.clipboard.readText().then(text => text === value)", arg=expected)


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        context = browser.new_context()
        context.grant_permissions(["clipboard-read", "clipboard-write"], origin=ORIGIN)
        context.route("**/*", serve)
        context.add_init_script("localStorage.setItem('auth_token',btoa('demo-admin:demo-only'));localStorage.setItem('username','demo-admin');")
        page = context.new_page()
        page.set_default_timeout(5000)
        page.goto(f"{ORIGIN}/hosts")
        for width in (1280, 390):
            page.set_viewport_size(dict(width=width, height=900))
            page.get_by_role("tab", name="临时凭据", exact=True).click()
            row = page.get_by_role("listitem").filter(has_text=RDP["target"])
            other = page.get_by_role("listitem").filter(has_text=OTHER["target"])
            expect(other.get_by_role("button", name="连接详情")).to_have_count(0)
            row.get_by_role("button", name="连接详情").click()
            dialog = page.get_by_role("dialog")
            expect(dialog.get_by_text(RDP["address"], exact=True)).to_be_visible()
            expect(dialog.get_by_text(PASSWORD, exact=True)).to_have_count(0)
            for label, value in (("地址", RDP["address"]), ("账号", RDP["username"]), ("密码", PASSWORD)):
                dialog.get_by_role("button", name=f"复制{label}", exact=True).click()
                clipboard(page, value)
            dialog.get_by_role("button", name="显示密码").click()
            expect(dialog.get_by_text(PASSWORD, exact=True)).to_be_visible()
            dialog.get_by_role("button", name="隐藏密码").click()
            expect(dialog.get_by_text(PASSWORD, exact=True)).to_have_count(0)
            expiry = page.evaluate("expiry => new Date(expiry).toLocaleString('zh-CN', {timeZoneName:'short'})", EXPIRY)
            dialog.get_by_role("button", name="一键复制（含有效期）").click()
            clipboard(page, f"地址：{RDP['address']}\n账号：{RDP['username']}\n密码：{PASSWORD}\n有效至：{expiry}")
            assert dialog.evaluate("node => node.scrollWidth <= node.clientWidth")
            page.keyboard.press("Escape")
            expect(dialog).to_have_count(0)
            expect(row.get_by_role("button", name="连接详情")).to_be_focused()
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")

        page.set_viewport_size(dict(width=1280, height=900))
        page.get_by_role("link", name="运行维护", exact=True).click()
        page.get_by_role("tab", name="临时凭据", exact=True).click()
        page.get_by_role("listitem").filter(has_text=VNC["target"]).get_by_role("button", name="连接详情").click()
        expect(dialog.get_by_role("link", name="打开屏幕共享")).to_have_attribute("href", VNC["address"])
        dialog.get_by_role("button", name="一键复制（含有效期）").click()
        clipboard(page, f"地址：{VNC['address']}\n账号：{VNC['username']}\n密码：{PASSWORD}\n有效至：{expiry}（仅可连接一次）")
        page.keyboard.press("Escape")

        page.get_by_role("listitem").filter(has_text=RDP["target"]).get_by_role("button", name="连接详情").click()
        state["certificate"] = False
        dialog.get_by_role("button", name="下载 .rdp").click()
        expect(page.get_by_text("证书指纹不匹配", exact=True)).to_be_visible()
        assert state["downloads"] == 0
        state["certificate"] = True
        with page.expect_download() as download:
            dialog.get_by_role("button", name="下载 .rdp").click()
        assert download.value.suggested_filename == "frp-agent-rdp-3.rdp"
        assert download.value.path().read_bytes() == RDP_FILE and state["downloads"] == 1

        state["admin"] = False
        page.goto(f"{ORIGIN}/hosts")
        page.get_by_role("article").filter(has_text="office-windows").get_by_role("button", name="连接详情").click()
        dialog.get_by_role("button", name="生成临时凭据", exact=True).click()
        expect(dialog.get_by_text(RDP["address"], exact=True)).to_be_visible()
        expect(dialog.get_by_text(PASSWORD, exact=True)).to_have_count(0)
        dialog.get_by_role("button", name="关闭", exact=True).click()
        expect(dialog).to_have_count(0)
        page.get_by_role("tab", name="临时凭据", exact=True).click()
        expect(page.get_by_text(OTHER["target"], exact=True)).to_have_count(0)
        page.get_by_role("listitem").filter(has_text=RDP["target"]).get_by_role("button", name="一键复制（含有效期）").click()
        clipboard(page, f"地址：{RDP['address']}\n账号：{RDP['username']}\n密码：{PASSWORD}\n有效至：{expiry}")
        assert state["copies"] == 8
        browser.close()
    print("Temporary credential details: desktop/mobile, SPA monitor, clipboard, RDP certificate/download and permissions passed")


if __name__ == "__main__":
    main()
