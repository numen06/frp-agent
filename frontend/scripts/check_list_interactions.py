"""Exercise multi-page lists and destructive confirmations against demo APIs only.

Run after npm run build with Vite preview on 127.0.0.1:4173.
No production requests or real credentials are used.
"""
from copy import deepcopy
from urllib.parse import parse_qs, unquote, urlparse

from playwright.sync_api import sync_playwright, expect

import capture_screenshots as demo


def seed():
    for rows, count, name_field, prefix in [
        (demo.SERVERS, 45, "name", "server"), (demo.HOSTS, 45, "name", "host"),
        (demo.KEYS, 45, "description", "demo-key"), (demo.PACKAGES, 45, "filename", "package"),
        (demo.SUBJECTS, 45, "name", "demo-user"),
    ]:
        originals = deepcopy(rows)
        rows[:] = [dict(originals[i % len(originals)], id=i+1, **{name_field: f"{prefix}-{i+1:03}"}) for i in range(count)]
    demo.GROUPS[:] = [dict(group_name=f"demo-{i:03}", total_count=3, online_count=3, offline_count=0) for i in range(45)]
    proxy = deepcopy(demo.PROXIES[0])
    demo.PROXIES[:] = [dict(proxy, id=i+1, name=f"demo-{i//3:03}_{['ssh','http','docker'][i%3]}", group_name=f"demo-{i//3:03}", local_port=[22,80,9000][i%3]) for i in range(135)]
    demo.GRANTS[:] = [dict(demo.GRANTS[0], id=i+1, host_id=i+1, host_name=f"host-{i+1:03}") for i in range(45)]
    original = deepcopy(demo.AUDIT[0])
    demo.AUDIT[:] = [dict(original, id=i+1, host_id=i%45+1, host_name=f"host-{i%45+1:03}", actor_type="user", actor_id=1, stdout="demo output\n"*80, stderr="", duration_ms=12) for i in range(65)]
    demo.RESPONSES["/api/managed-hosts/2/docker/containers"]["containers"] = [dict(Id=f"demo-container-{i:03}", Names=[f"/demo-{i:03}"], Image="demo/example:latest", Status="Up") for i in range(45)]


def main():
    seed()
    errors, requests, mutations = [], [], []

    def intercept(route):
        url = urlparse(route.request.url)
        if url.netloc != "127.0.0.1:4173":
            errors.append("External request blocked")
            route.abort(); return
        if not url.path.startswith("/api/"):
            route.continue_(); return
        requests.append((url.path, parse_qs(url.query)))
        if route.request.method != "GET":
            data = route.request.post_data_json if route.request.post_data else {}
            mutations.append((route.request.method, url.path, data, parse_qs(url.query)))
            if url.path == "/api/managed-hosts/audit/cleanup":
                route.fulfill(json=dict(count=7, deleted=0 if data.get("dry_run", True) else 7)); return
            if url.path == "/api/managed-hosts/audit/delete":
                route.fulfill(json=dict(deleted=len(data["ids"]))); return
            if url.path == "/api/groups/create":
                name = data["group_name"]
                demo.GROUPS.append(dict(group_name=name, total_count=3, online_count=0, offline_count=3))
                route.fulfill(json=dict(success=True, group_name=name, created_proxies=3)); return
            if route.request.method == "DELETE" and url.path.startswith("/api/groups/"):
                name = unquote(url.path.rsplit("/", 1)[-1])
                demo.GROUPS[:] = [row for row in demo.GROUPS if row["group_name"] != name]
                route.fulfill(json=dict(success=True, message="演示分组已删除", affected_count=3, released_ports=3)); return
            errors.append(f"Unexpected mutation: {route.request.method} {url.path}")
            route.fulfill(status=501, json=dict(detail="No demo mutation defined")); return
        payload = demo.demo_response(url)
        if payload is None:
            errors.append(f"Unmocked GET: {url.path}")
            route.fulfill(status=501, json=dict(detail="No demo response defined"))
        else:
            route.fulfill(json=payload)

    with sync_playwright() as p:
        browser = p.chromium.launch()
        context = browser.new_context(viewport=dict(width=1280, height=900), locale="zh-CN", reduced_motion="reduce", service_workers="block")
        context.route("**/*", intercept)
        context.add_init_script("localStorage.setItem('auth_token', btoa('demo-admin:demo-only'));localStorage.setItem('username','demo-admin');localStorage.setItem('currentServerId','1');localStorage.setItem('default_api_key_id','41')")
        page = context.new_page()
        page.on("pageerror", lambda e: errors.append(str(e)))

        def settle():
            page.wait_for_load_state("networkidle")
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth"), page.url

        def goto(path):
            page.goto(demo.BASE + path); settle()

        def next_page(width):
            page.get_by_role("button" if width < 768 else "link", name="下一页", exact=True).last.click(); settle()

        for width in [1280, 390]:
            page.set_viewport_size(dict(width=width, height=900))
            for route in ["servers", "api-keys", "proxies", "groups", "packages", "hosts"]:
                goto("/" + route)
                next_page(width)
                assert any(query.get("page") == ["2"] for _, query in requests), route
                if route != "hosts":
                    if width >= 768:
                        expect(page.locator("main table:visible tbody tr")).to_have_count(20)
                if route == "api-keys":
                    page.wait_for_function("localStorage.getItem('default_api_key_id') === '41'")
            for tab in ["访问授权", "系统用户", "访问审计"]:
                goto("/hosts")
                page.get_by_role("button", name=tab, exact=True).click(); settle()
                next_page(width)
            print(f"Paged desktop/mobile management lists: {width}px", flush=True)

            # A teleported menu stays next to the clicked button and inside the viewport.
            goto("/proxies")
            trigger = page.get_by_role("button", name="添加菜单", exact=True)
            trigger.click()
            menu = page.get_by_role("link", name="添加代理", exact=True).locator("..")
            rect, anchor = menu.bounding_box(), trigger.bounding_box()
            assert rect["x"] >= 7 and rect["y"] > 30 and rect["x"] + rect["width"] <= width
            assert min(abs(rect["y"] - anchor["y"] - anchor["height"]), abs(rect["y"] + rect["height"] - anchor["y"])) <= 9
            page.set_viewport_size(dict(width=width, height=600)); settle()
            rect = menu.bounding_box(); assert rect["y"] + rect["height"] <= 600
            page.keyboard.press("Escape"); assert not menu.is_visible()
            page.set_viewport_size(dict(width=width, height=900))

            # An option on the third page can be selected without loading the catalog in advance.
            goto("/proxies")
            page.get_by_role("button", name="选择服务器", exact=True).click(); settle()
            next_page(width); next_page(width)
            page.get_by_role("button", name="server-045", exact=True).click(); settle()
            assert page.evaluate("localStorage.getItem('currentServerId')") == "45"
            assert page.get_by_role("button", name="选择服务器", exact=True).inner_text().startswith("server-045")
            print(f"Anchored menu, Escape and cross-page selector: {width}px", flush=True)

        # Cancel does not call DELETE; a non-empty group has two confirmation stages.
        page.set_viewport_size(dict(width=390, height=844)); goto("/groups")
        page.get_by_role("button", name="更多操作", exact=True).first.click()
        menu = page.locator(".group-more-menu")
        assert menu.bounding_box()["x"] > 0 and menu.bounding_box()["y"] > 0
        menu.get_by_role("button", name="删除", exact=True).click(); settle()
        dialog = page.get_by_role("dialog", name="删除分组", exact=True)
        page.get_by_role("button", name="继续删除", exact=True).click()
        expect(page.get_by_role("button", name="确认全部删除", exact=True)).to_be_disabled()
        page.get_by_label("确认删除的分组名称").fill("wrong")
        expect(page.get_by_role("button", name="确认全部删除", exact=True)).to_be_disabled()
        page.get_by_role("button", name="取消", exact=True).last.click()
        assert not any(method == "DELETE" for method, *_ in mutations)
        page.get_by_role("button", name="更多操作", exact=True).first.click()
        menu.get_by_role("button", name="删除", exact=True).click(); settle()
        name = demo.GROUPS[0]["group_name"]
        page.get_by_role("button", name="继续删除", exact=True).click()
        page.get_by_label("确认删除的分组名称").fill(name)
        page.get_by_role("button", name="确认全部删除", exact=True).click(); settle()
        deletion = next(row for row in mutations if row[0] == "DELETE")
        assert deletion[3]["delete_proxies"] == ["true"] and deletion[3]["expected_proxy_count"] == ["3"]
        expect(dialog).not_to_be_visible()

        page.get_by_role("button", name="新增分组", exact=True).click()
        page.locator(".app-dialog:visible input[type=text]").fill("demo-created")
        page.get_by_role("button", name="创建并使用", exact=True).click(); settle()
        assert any(path == "/api/groups/create" and data.get("create_defaults") for _, path, data, _ in mutations)
        assert page.locator(".app-dialog:visible").count() == 1
        expect(page.get_by_role("heading", name="生成分组配置 - demo-created", exact=True)).to_be_visible()
        page.keyboard.press("Escape")

        goto("/hosts")
        page.get_by_role("button", name="访问审计", exact=True).click(); settle()
        page.get_by_role("button", name="详情", exact=True).first.click(); settle()
        detail = page.get_by_role("dialog", name="审计日志详情", exact=True)
        for height in [844, 420]:
            page.set_viewport_size(dict(width=390, height=height))
            page.wait_for_function('Math.abs(parseFloat(getComputedStyle(document.documentElement).getPropertyValue("--app-viewport-height")) - innerHeight) < 2')
            rect = detail.locator(".app-dialog-panel").bounding_box()
            assert abs(rect["y"]) < 2 and abs(rect["height"] - height) < 2
            detail.get_by_role("button", name="关闭详情").click(trial=True)
        detail.get_by_role("button", name="关闭详情").click()
        page.set_viewport_size(dict(width=390, height=844))
        page.get_by_role("button", name="清理旧日志", exact=True).click()
        page.get_by_role("button", name="预览影响数量", exact=True).click(); settle()
        expect(page.get_by_role("button", name="确认清理", exact=True)).to_be_enabled()
        page.get_by_role("spinbutton").fill("30")
        expect(page.get_by_role("button", name="确认清理", exact=True)).to_be_disabled()
        page.get_by_role("button", name="预览影响数量", exact=True).click(); settle()
        page.once("dialog", lambda dialog: dialog.accept())
        page.get_by_role("button", name="确认清理", exact=True).click(); settle()
        assert any(path.endswith("/audit/cleanup") and data.get("dry_run") is False for _, path, data, _ in mutations)
        expect(page.get_by_role("dialog", name="清理旧日志", exact=True)).not_to_be_visible()
        assert page.evaluate("document.body.style.overflow") != "hidden"
        print("Group create/use, two-stage deletion, audit details and cleanup preview passed", flush=True)
        browser.close()
    assert not errors, "\n".join(errors)
    print("All interactions passed against isolated demo APIs.", flush=True)


if __name__ == "__main__":
    main()
