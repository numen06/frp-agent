#!/usr/bin/env python3
"""
本地验证：读取 test-data/sample-frpc-import.ini，调用 POST /api/groups/import-config。

用法（在仓库根目录）:
  cd backend
  ..\\.venv\\Scripts\\python.exe scripts\\try_group_import_ini.py

或指定分组名:
  python scripts/try_group_import_ini.py --group mylocal
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# 保证能 import app
BACKEND_ROOT = Path(__file__).resolve().parent.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from fastapi.testclient import TestClient

from app.database import SessionLocal
from app.main import app
from app.models.frps_server import FrpsServer
from app.routers.group import _auth_for_script


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--group", default="localtest", help="导入目标分组名")
    args = parser.parse_args()

    repo_root = BACKEND_ROOT.parent
    ini_path = repo_root / "test-data" / "sample-frpc-import.ini"
    if not ini_path.is_file():
        print(f"缺少示例文件: {ini_path}")
        return 1

    content = ini_path.read_text(encoding="utf-8")

    db = SessionLocal()
    try:
        row = db.query(FrpsServer.id).order_by(FrpsServer.id.asc()).first()
        if not row:
            print("数据库中没有任何 frps 服务器，请先在界面添加一台服务器后再试。")
            return 1
        frps_server_id = row[0]
    finally:
        db.close()

    app.dependency_overrides[_auth_for_script] = lambda: {
        "type": "api_key",
        "obj": None,
        "key": "local-script",
    }

    client = TestClient(app)
    payload = {
        "frps_server_id": frps_server_id,
        "group_name": args.group,
        "config_content": content,
        "config_format": "ini",
        "overwrite": True,
    }
    r = client.post(
        "/api/groups/import-config",
        json=payload,
        headers={"X-API-Key": "dummy"},
    )
    print("HTTP", r.status_code)
    try:
        data = r.json()
    except Exception:
        print(r.text)
        return 1
    print(json.dumps(data, indent=2, ensure_ascii=False))
    return 0 if r.status_code == 200 and data.get("success") else 1


if __name__ == "__main__":
    raise SystemExit(main())
