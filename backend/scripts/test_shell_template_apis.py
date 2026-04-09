#!/usr/bin/env python3
"""
自检：app/script_templates 下模板可加载，且依赖这些模板的 HTTP 接口返回 200。

覆盖：import-script、import-config（示例 INI）、quick-install/download、
packages install/upgrade-script、config script linux/windows/systemd。

在 backend 目录执行:
  ..\\.venv\\Scripts\\python.exe scripts\\test_shell_template_apis.py
"""
from __future__ import annotations

import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parent.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from fastapi.testclient import TestClient

from app.auth import get_current_user
from app.database import SessionLocal
from app.main import app
from app.models.frp_package import FrpPackage
from app.models.frps_server import FrpsServer
from app.models.user import User
from app.routers import frp_package, group
from app.script_templates import list_script_template_names, load_shell_template


def _configure_stdio_utf8() -> None:
    for stream in (sys.stdout, sys.stderr):
        reconf = getattr(stream, "reconfigure", None)
        if callable(reconf):
            try:
                reconf(encoding="utf-8")
            except Exception:
                pass


def _ok(name: str) -> None:
    print(f"  [OK] {name}")


def _fail(name: str, detail: str) -> None:
    print(f"  [FAIL] {name}: {detail}")


def test_templates_on_disk() -> bool:
    print("== 模板文件 load_shell_template ==")
    ok = True
    for name in list_script_template_names():
        try:
            body = load_shell_template(name)
            if len(body) < 20:
                _fail(name, "内容过短")
                ok = False
            else:
                _ok(name)
        except Exception as e:
            _fail(name, str(e))
            ok = False
    return ok


def main() -> int:
    _configure_stdio_utf8()
    if not test_templates_on_disk():
        return 1

    dummy_user = User(id=1, username="shell-template-test", password_hash="")

    def fake_script_auth():
        return {"type": "api_key", "obj": None, "key": "local-test"}

    def fake_current_user():
        return dummy_user

    print("== HTTP 接口（TestClient）==")
    app.dependency_overrides[group._auth_for_script] = fake_script_auth
    app.dependency_overrides[frp_package._auth_for_install_script] = fake_script_auth
    app.dependency_overrides[get_current_user] = fake_current_user

    try:
        client = TestClient(app)

        r = client.get(
            "/api/groups/import-script",
            params={
                "frps_server_id": 1,
                "group_name": "t",
                "config_path": "/opt/frp",
                "api_key": "x",
            },
        )
        if r.status_code == 200 and "SCAN_PATH=" in r.text and "PY_FOR_BASH" not in r.text:
            _ok("GET /api/groups/import-script")
        else:
            _fail("GET /api/groups/import-script", f"status={r.status_code} head={r.text[:120]!r}")
            return 1

        repo_root = BACKEND_ROOT.parent
        sample_ini = repo_root / "test-data" / "sample-frpc-import.ini"
        db = SessionLocal()
        try:
            frps_row = db.query(FrpsServer.id).order_by(FrpsServer.id.asc()).first()
        finally:
            db.close()
        if sample_ini.is_file() and frps_row:
            r = client.post(
                "/api/groups/import-config",
                json={
                    "frps_server_id": frps_row[0],
                    "group_name": "shell_template_api_smoke",
                    "config_content": sample_ini.read_text(encoding="utf-8"),
                    "config_format": "ini",
                    "overwrite": True,
                },
                headers={"X-API-Key": "x"},
            )
            try:
                data = r.json()
            except Exception:
                data = {}
            if r.status_code == 200 and data.get("success"):
                _ok("POST /api/groups/import-config (sample-frpc-import.ini)")
            else:
                _fail(
                    "POST /api/groups/import-config",
                    f"status={r.status_code} body={r.text[:200]!r}",
                )
                return 1
        else:
            print(
                "  [SKIP] POST /api/groups/import-config：需要 test-data/sample-frpc-import.ini 且库中至少一台 frps"
            )

        db = SessionLocal()
        try:
            pkg = (
                db.query(FrpPackage)
                .filter(FrpPackage.is_active == True, FrpPackage.platform == "linux_amd64")
                .order_by(FrpPackage.id.desc())
                .first()
            )
        finally:
            db.close()

        if pkg:
            r = client.get(
                f"/api/groups/g/quick-install",
                params={"server_name": "s", "api_key": "x"},
            )
            if r.status_code == 200 and "Downloading" in r.text and "frpc.toml" in r.text:
                _ok("GET /api/groups/{g}/quick-install")
            else:
                _fail("quick-install", f"status={r.status_code} head={r.text[:160]!r}")
                return 1

            r = client.get(
                f"/api/groups/g/quick-download",
                params={"server_name": "s", "api_key": "x"},
            )
            if r.status_code == 200 and "downloaded" in r.text:
                _ok("GET /api/groups/{g}/quick-download")
            else:
                _fail("quick-download", f"status={r.status_code} head={r.text[:160]!r}")
                return 1

            r = client.get(
                f"/api/groups/g/deploy",
                params={
                    "server_name": "s",
                    "api_key": "x",
                    "upgrade": "true",
                    "force_config": "true",
                },
            )
            if (
                r.status_code == 200
                and "frp-client deploy script" in r.text
                and 'UPGRADE="true"' in r.text
                and 'FORCE_CONFIG="true"' in r.text
                and "{{upgrade}}" not in r.text
            ):
                _ok("GET /api/groups/{g}/deploy")
            else:
                _fail("deploy", f"status={r.status_code} head={r.text[:200]!r}")
                return 1

            r = client.get(
                "/api/packages/install-script",
                params={"package_id": pkg.id, "install_path": "/opt/frp", "api_key": "x"},
            )
            if r.status_code == 200 and "frp-client install script" in r.text:
                _ok("GET /api/packages/install-script")
            else:
                _fail("install-script", f"status={r.status_code} head={r.text[:120]!r}")
                return 1

            r = client.get(
                "/api/packages/upgrade-script",
                params={"package_id": pkg.id, "install_path": "/opt/frp", "api_key": "x"},
            )
            if r.status_code == 200 and "frp-client upgrade script" in r.text:
                _ok("GET /api/packages/upgrade-script")
            else:
                _fail("upgrade-script", f"status={r.status_code} head={r.text[:120]!r}")
                return 1
        else:
            print(
                "  [SKIP] 无激活的 linux_amd64 安装包：quick-install / quick-download / deploy / install-script / upgrade-script"
            )

        r = client.get("/api/config/script/linux", params={"frpc_path": "/bin/frpc", "config_path": "/etc/frp.toml"})
        if r.status_code == 200 and "/bin/frpc" in r.text and "case" in r.text:
            _ok("GET /api/config/script/linux")
        else:
            _fail("config/script/linux", f"status={r.status_code}")
            return 1

        r = client.get(
            "/api/config/script/windows",
            params={"frpc_path": "C:\\frp\\frpc.exe", "config_path": "C:\\frp\\frpc.toml"},
        )
        if r.status_code == 200 and "frpc.exe" in r.text:
            _ok("GET /api/config/script/windows")
        else:
            _fail("config/script/windows", f"status={r.status_code}")
            return 1

        r = client.get(
            "/api/config/script/systemd",
            params={
                "frpc_path": "/usr/bin/frpc",
                "config_path": "/etc/frp/frpc.toml",
                "user": "frp",
            },
        )
        if r.status_code == 200 and "[Service]" in r.text and "User=frp" in r.text:
            _ok("GET /api/config/script/systemd")
        else:
            _fail("config/script/systemd", f"status={r.status_code} body={r.text[:200]!r}")
            return 1

    finally:
        app.dependency_overrides.clear()

    print("全部通过。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
