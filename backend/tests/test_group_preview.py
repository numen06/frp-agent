"""分组动作上下文与命令预览"""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models.frp_package import FrpPackage
from app.models.frps_server import FrpsServer
from app.models.proxy import Proxy
from app.routers.group import (
    DeployPreviewRequest,
    ImportPreviewRequest,
    _compose_action_context,
    _compose_deploy_preview,
    _compose_import_preview,
)


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def _seed_server(db, name="srv1"):
    server = FrpsServer(
        name=name,
        server_addr="1.2.3.4",
        server_port=7000,
        api_base_url="http://x/api",
        auth_username="a",
        auth_password="b",
    )
    db.add(server)
    db.commit()
    db.refresh(server)
    return server


def _seed_package(db, tmp_path, platform="linux_amd64", version="0.61.1", file_exists=True):
    package_path = tmp_path / f"frpc_{platform}.tar.gz"
    if file_exists:
        package_path.write_bytes(b"package")
    pkg = FrpPackage(
        filename="frpc_linux_amd64.tar.gz",
        platform=platform,
        version=version,
        file_path=str(package_path),
        file_size=package_path.stat().st_size if file_exists else 0,
        is_active=True,
    )
    db.add(pkg)
    db.commit()
    return pkg


def test_action_context_returns_summary(db, tmp_path):
    server = _seed_server(db)
    _seed_package(db, tmp_path)
    db.add(
        Proxy(
            frps_server_id=server.id,
            name="demo_ssh",
            group_name="demo",
            proxy_type="tcp",
            local_ip="127.0.0.1",
            local_port=22,
            remote_port=6001,
            status="online",
        )
    )
    db.commit()

    ctx = _compose_action_context(db, "demo", server.id)
    assert ctx["group_name"] == "demo"
    assert ctx["summary"]["total"] == 1
    assert ctx["summary"]["online"] == 1
    assert ctx["capabilities"]["deploy"]["enabled"] is True
    assert ctx["defaults"]["install_path"] == "/opt/frp"


def test_deploy_preview_missing_api_key(db, tmp_path):
    server = _seed_server(db)
    _seed_package(db, tmp_path)
    body = DeployPreviewRequest(frps_server_id=server.id, server_name=server.name)
    result = _compose_deploy_preview(db, "demo", body, "http://localhost:8000")

    assert result["command"] == ""
    codes = [m["code"] for m in result["missing_requirements"]]
    assert "api_key_missing" in codes


def test_deploy_preview_builds_command(db, tmp_path):
    server = _seed_server(db)
    _seed_package(db, tmp_path)
    body = DeployPreviewRequest(
        frps_server_id=server.id,
        server_name=server.name,
        api_key="test-key",
    )
    result = _compose_deploy_preview(db, "demo", body, "http://localhost:8000")

    assert result["command"].startswith('curl -sL "http://localhost:8000/api/groups/demo/deploy?')
    assert "api_key=test-key" in result["command"]
    assert result["missing_requirements"] == []
    assert result["effective_options"]["install_path"] == "/opt/frp"


def test_deploy_preview_ignores_unready_package(db, tmp_path):
    server = _seed_server(db)
    _seed_package(db, tmp_path, file_exists=False)
    body = DeployPreviewRequest(
        frps_server_id=server.id,
        server_name=server.name,
        api_key="test-key",
    )
    result = _compose_deploy_preview(db, "demo", body, "http://localhost:8000")

    assert result["command"] == ""
    assert result["package_available"] is False
    assert any(m["code"] == "package_missing" for m in result["missing_requirements"])


def test_import_preview_builds_command(db):
    server = _seed_server(db)
    body = ImportPreviewRequest(
        frps_server_id=server.id,
        group_name="demo",
        api_key="test-key",
    )
    result = _compose_import_preview(db, body, "http://localhost:8000")

    assert result["command"].startswith('curl -sL "http://localhost:8000/api/groups/import-script?')
    assert "group_name=demo" in result["command"]
    assert result["missing_requirements"] == []


def test_import_preview_missing_group_name(db):
    server = _seed_server(db)
    body = ImportPreviewRequest(
        frps_server_id=server.id,
        group_name="  ",
        api_key="test-key",
    )
    result = _compose_import_preview(db, body, "http://localhost:8000")
    assert result["command"] == ""
    assert any(m["code"] == "group_name_missing" for m in result["missing_requirements"])
