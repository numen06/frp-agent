"""FRP 安装包管理路由"""
import json
import os
import re
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query, Request, status, Body
from fastapi.responses import FileResponse, PlainTextResponse
from sqlalchemy.orm import Session

from app.auth import get_current_user, verify_api_key
from app.database import get_db
from app.models.user import User
from app.models.frp_package import FrpPackage
from app.schemas.frp_package import FrpPackageResponse, FrpPackageSyncRequest
from app.config import get_settings
from app.services.github_service import GithubService

router = APIRouter(prefix="/api/packages", tags=["安装包管理"])

# 手动上传时的平台标识格式（与 GitHub 资源名中的平台段风格一致，不枚举具体值）
_UPLOAD_PLATFORM_PATTERN = re.compile(r"^[a-zA-Z0-9_]+$")


def _merge_platform_lists(*lists) -> List[str]:
    seen = set()
    out: List[str] = []
    for lst in lists:
        for p in lst or []:
            if p and p not in seen:
                seen.add(p)
                out.append(p)
    return out


def _ensure_packages_dir() -> str:
    settings = get_settings()
    current_file = os.path.abspath(__file__)
    app_dir = os.path.dirname(os.path.dirname(current_file))
    backend_dir = os.path.dirname(app_dir)
    project_root = os.path.dirname(backend_dir)
    packages_dir = os.path.join(project_root, settings.packages_dir)
    os.makedirs(packages_dir, exist_ok=True)
    return packages_dir


def _require_api_key_only(request: Request, db: Session = Depends(get_db)):
    authorization = request.headers.get("Authorization", "")
    api_key = request.query_params.get("api_key")
    if authorization.startswith("Bearer "):
        api_key = authorization[7:].strip()
    if not api_key:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="仅支持 API Key 认证")
    api_key_obj = verify_api_key(db, api_key)
    if not api_key_obj:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="API Key 无效或已过期")
    return api_key_obj


def _scripts_file_path() -> str:
    return os.path.join(_ensure_packages_dir(), "install_scripts.json")


def _default_template_for_platform(platform: str) -> str:
    if platform.startswith("windows_"):
        return (
            "# frp-client install script (PowerShell)\n"
            "# platform: {{platform}}  version: {{version}}\n"
            "\n"
            "$ErrorActionPreference = 'Stop'\n"
            "$FRP_DIR = 'C:\\frp'\n"
            "$FRPC_EXE = \"$FRP_DIR\\frpc.exe\"\n"
            "\n"
            "# --- 创建目录 ---\n"
            "New-Item -ItemType Directory -Force -Path $FRP_DIR | Out-Null\n"
            "\n"
            "# --- 下载并解压 frpc ---\n"
            "Write-Host \"Downloading {{filename}} ...\"\n"
            "Invoke-WebRequest -Uri \"{{download_url}}\" -OutFile \"$env:TEMP\\{{filename}}\"\n"
            "tar -xf \"$env:TEMP\\{{filename}}\" -C \"$env:TEMP\"\n"
            "Copy-Item \"$env:TEMP\\frp_*\\frpc.exe\" $FRPC_EXE -Force\n"
            "\n"
            "# --- 清理临时文件 ---\n"
            "Remove-Item \"$env:TEMP\\{{filename}}\" -Force -ErrorAction SilentlyContinue\n"
            "Get-ChildItem \"$env:TEMP\\frp_*\" -Directory | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue\n"
            "\n"
            "# --- 配置文件（仅当不存在时下载，不覆盖已有配置）---\n"
            "{{config_line}}\n"
            "\n"
            "# --- 配置兼容性：frpc.ini -> frpc.toml 迁移 ---\n"
            "$INI_FILE = \"$FRP_DIR\\frpc.ini\"\n"
            "$TOML_FILE = \"$FRP_DIR\\frpc.toml\"\n"
            "if (Test-Path $INI_FILE) {\n"
            "    if (-not (Test-Path $TOML_FILE)) {\n"
            "        Write-Host \"迁移到 TOML: 将 $INI_FILE 重命名为 $TOML_FILE\"\n"
            "        Move-Item $INI_FILE $TOML_FILE\n"
            "    } else {\n"
            "        $ts = Get-Date -Format 'yyyyMMdd_HHmmss'\n"
            "        Move-Item $INI_FILE \"$INI_FILE.backup_$ts\"\n"
            "        Write-Host \"警告: $INI_FILE 存在但 $TOML_FILE 已存在，已备份为 $INI_FILE.backup_$ts\"\n"
            "    }\n"
            "}\n"
            "\n"
            "Write-Host \"=== Frp Client 部署完成 ===\"\n"
            "Write-Host \"安装路径: $FRPC_EXE\"\n"
        )
    # Linux / macOS / 其他平台
    return (
        "#!/usr/bin/env bash\n"
        "# frp-client install script\n"
        "# platform: {{platform}}  version: {{version}}\n"
        "set -e\n"
        "\n"
        "FRP_DIR=\"/opt/frp\"\n"
        "FRPC_BIN=\"$FRP_DIR/frpc\"\n"
        "\n"
        "# --- 创建目录 ---\n"
        "mkdir -p \"$FRP_DIR\"\n"
        "\n"
        "# --- 下载并解压 frpc ---\n"
        "echo \"Downloading {{filename}} ...\"\n"
        "curl -sL \"{{download_url}}\" -o /tmp/{{filename}}\n"
        "cd /tmp\n"
        "tar -xzf \"{{filename}}\"\n"
        "cp frp_*/frpc \"$FRPC_BIN\"\n"
        "chmod 755 \"$FRPC_BIN\"\n"
        "\n"
        "# --- 清理临时文件 ---\n"
        "rm -f /tmp/{{filename}}\n"
        "rm -rf /tmp/frp_*\n"
        "\n"
        "# --- 配置文件（仅当不存在时下载，不覆盖已有配置）---\n"
        "if [[ ! -f \"$FRP_DIR/frpc.toml\" ]]; then\n"
        "    {{config_line}}\n"
        "else\n"
        "    echo \"检测到已有配置文件 $FRP_DIR/frpc.toml，跳过下载以保留用户配置。\"\n"
        "fi\n"
        "\n"
        "# --- 配置兼容性：frpc.ini -> frpc.toml 迁移 ---\n"
        "INI_FILE=\"$FRP_DIR/frpc.ini\"\n"
        "TOML_FILE=\"$FRP_DIR/frpc.toml\"\n"
        "if [[ -f \"$INI_FILE\" ]]; then\n"
        "    if [[ ! -f \"$TOML_FILE\" ]]; then\n"
        "        echo \"迁移到 TOML: 将 $INI_FILE 重命名为 $TOML_FILE\"\n"
        "        mv \"$INI_FILE\" \"$TOML_FILE\"\n"
        "    else\n"
        "        echo \"警告: $INI_FILE 存在但 $TOML_FILE 已存在，跳过迁移以防止覆盖。\"\n"
        "        mv \"$INI_FILE\" \"${INI_FILE}.backup_$(date +%Y%m%d_%H%M%S)\"\n"
        "    fi\n"
        "fi\n"
        "\n"
        "echo \"=== Frp Client 部署完成 ===\"\n"
        "echo \"安装路径: $FRPC_BIN\"\n"
    )


def _load_script_templates() -> dict:
    path = _scripts_file_path()
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _save_script_templates(data: dict):
    path = _scripts_file_path()
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


@router.get("", response_model=List[FrpPackageResponse])
def list_packages(
    version: Optional[str] = Query(None),
    platform: Optional[str] = Query(None),
    source: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(FrpPackage)
    if version:
        query = query.filter(FrpPackage.version == version)
    if platform:
        query = query.filter(FrpPackage.platform == platform)
    if source:
        query = query.filter(FrpPackage.source == source)
    return query.order_by(FrpPackage.downloaded_at.desc()).offset(skip).limit(limit).all()


@router.post("/upload", response_model=FrpPackageResponse)
async def upload_package(
    version: str = Form(...),
    platform: str = Form(...),
    package_file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not _UPLOAD_PLATFORM_PATTERN.match(platform or ""):
        raise HTTPException(
            status_code=400,
            detail="平台标识格式无效，请使用与官方发布包一致的平台名（如 linux_amd64），仅字母数字下划线",
        )

    packages_dir = _ensure_packages_dir()
    filename = package_file.filename or f"frp_{version}_{platform}.bin"
    target_name = f"{version}_{platform}_{filename}"
    save_path = os.path.join(packages_dir, target_name)

    with open(save_path, "wb") as f:
        content = await package_file.read()
        f.write(content)

    service = GithubService()
    checksum = service.calculate_sha256(save_path)
    size = os.path.getsize(save_path)

    existed = db.query(FrpPackage).filter(
        FrpPackage.version == version,
        FrpPackage.platform == platform
    ).first()
    if existed:
        if os.path.exists(existed.file_path) and existed.file_path != save_path:
            os.remove(existed.file_path)
        existed.filename = filename
        existed.file_path = save_path
        existed.file_size = size
        existed.source = "upload"
        existed.download_url = None
        existed.sha256_checksum = checksum
        existed.downloaded_at = datetime.utcnow()
        db.commit()
        db.refresh(existed)
        return existed

    item = FrpPackage(
        version=version,
        platform=platform,
        filename=filename,
        file_path=save_path,
        file_size=size,
        source="upload",
        download_url=None,
        is_active=True,
        sha256_checksum=checksum,
        downloaded_at=datetime.utcnow(),
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.get("/releases")
async def list_releases(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = GithubService()
    releases = await service.fetch_releases()
    out = []
    for x in releases:
        platforms = service.discover_platforms_from_release(x)
        out.append(
            {
                "version": x.get("tag_name"),
                "name": x.get("name"),
                "published_at": x.get("published_at"),
                "platforms": platforms,
            }
        )
    return out


@router.get("/platforms")
async def get_supported_platforms(
    version: Optional[str] = Query(
        None,
        description="Release tag，如 v0.61.1；不传则取 GitHub 最新 Release",
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = GithubService()
    releases = await service.fetch_releases()
    if not releases:
        return {"platforms": [], "version": None, "source": "github"}
    if version:
        tag = version
    else:
        tag = releases[0].get("tag_name")
    platforms = await service.discover_platforms_for_tag(tag) if tag else []
    # 合并本地已存在的平台（历史数据/手动上传）
    local_rows = db.query(FrpPackage.platform).distinct().all()
    local_platforms = [r[0] for r in local_rows if r[0]]
    merged = _merge_platform_lists(platforms, local_platforms)
    return {"platforms": merged, "version": tag, "source": "github"}


@router.get("/script-templates")
async def get_script_templates(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = GithubService()
    releases = await service.fetch_releases()
    discovered: List[str] = []
    if releases:
        discovered = service.discover_platforms_from_release(releases[0])
    templates = _load_script_templates()
    local_rows = db.query(FrpPackage.platform).distinct().all()
    local_platforms = [r[0] for r in local_rows if r[0]]
    all_keys = _merge_platform_lists(discovered, list(templates.keys()), local_platforms)
    result = {}
    for platform in all_keys:
        result[platform] = templates.get(platform) or _default_template_for_platform(platform)
    return result


@router.put("/script-templates/{platform}")
def update_script_template(
    platform: str,
    payload: dict = Body(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not _UPLOAD_PLATFORM_PATTERN.match(platform or ""):
        raise HTTPException(status_code=400, detail="平台标识格式无效")
    script_template = (payload or {}).get("script_template", "")
    if not script_template or not isinstance(script_template, str):
        raise HTTPException(status_code=400, detail="script_template 不能为空")
    templates = _load_script_templates()
    templates[platform] = script_template
    _save_script_templates(templates)
    return {"platform": platform, "saved": True}


@router.post("/sync")
async def sync_from_github(
    payload: FrpPackageSyncRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = GithubService()
    releases = await service.fetch_releases()
    release = next((x for x in releases if x.get("tag_name") == payload.version), None)
    if not release:
        raise HTTPException(status_code=404, detail="未找到对应版本")

    discovered = set(service.discover_platforms_from_release(release))
    if not discovered:
        raise HTTPException(status_code=400, detail="该版本 Release 中未解析到任何 frp 安装包资源")

    if payload.platforms:
        selected_platforms = [p for p in payload.platforms if p in discovered]
    else:
        selected_platforms = sorted(discovered)
    if not selected_platforms:
        raise HTTPException(status_code=400, detail="未选择有效平台（请从该版本 Release 提供的平台中选择）")

    assets = release.get("assets", [])
    packages_dir = _ensure_packages_dir()
    results = []
    for asset in assets:
        name = asset.get("name", "")
        platform = service.parse_platform_from_filename(name)
        if not platform or platform not in selected_platforms:
            continue
        url = asset.get("browser_download_url")
        if not url:
            continue

        save_path = os.path.join(packages_dir, name)
        size = await service.download_asset(url, save_path)
        checksum = service.calculate_sha256(save_path)

        existed = db.query(FrpPackage).filter(
            FrpPackage.version == payload.version,
            FrpPackage.platform == platform
        ).first()

        if existed:
            if os.path.exists(existed.file_path) and existed.file_path != save_path:
                os.remove(existed.file_path)
            existed.filename = name
            existed.file_path = save_path
            existed.file_size = size
            existed.source = "github"
            existed.download_url = url
            existed.sha256_checksum = checksum
            existed.downloaded_at = datetime.utcnow()
            db.commit()
            db.refresh(existed)
            results.append(existed)
        else:
            item = FrpPackage(
                version=payload.version,
                platform=platform,
                filename=name,
                file_path=save_path,
                file_size=size,
                source="github",
                download_url=url,
                is_active=True,
                sha256_checksum=checksum,
                downloaded_at=datetime.utcnow(),
            )
            db.add(item)
            db.commit()
            db.refresh(item)
            results.append(item)

    return {"version": payload.version, "count": len(results), "items": results}


@router.post("/sync/check")
async def check_updates(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = GithubService()
    releases = await service.fetch_releases()
    latest = releases[0].get("tag_name") if releases else None
    newest_local = db.query(FrpPackage).order_by(FrpPackage.downloaded_at.desc()).first()
    return {
        "latest_version": latest,
        "local_version": newest_local.version if newest_local else None,
        "has_update": bool(latest and (not newest_local or newest_local.version != latest)),
    }


@router.delete("/{package_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_package(
    package_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    item = db.query(FrpPackage).filter(FrpPackage.id == package_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="安装包不存在")
    if os.path.exists(item.file_path):
        os.remove(item.file_path)
    db.delete(item)
    db.commit()
    return None


@router.get("/{package_id}/download")
def download_package(
    package_id: int,
    api_key_obj=Depends(_require_api_key_only),
    db: Session = Depends(get_db),
):
    item = db.query(FrpPackage).filter(FrpPackage.id == package_id, FrpPackage.is_active == True).first()
    if not item:
        raise HTTPException(status_code=404, detail="安装包不存在")
    if not os.path.exists(item.file_path):
        raise HTTPException(status_code=404, detail="安装包文件不存在")
    return FileResponse(path=item.file_path, filename=item.filename, media_type="application/octet-stream")


@router.get("/install-script")
def get_install_script(
    package_id: int = Query(..., ge=1),
    install_path: str = Query("/usr/local/bin"),
    config_url: Optional[str] = Query(None),
    request: Request = None,
    api_key_obj=Depends(_require_api_key_only),
    db: Session = Depends(get_db),
):
    item = db.query(FrpPackage).filter(FrpPackage.id == package_id, FrpPackage.is_active == True).first()
    if not item:
        raise HTTPException(status_code=404, detail="安装包不存在")

    api_key = request.query_params.get("api_key")
    server_base = f"{request.url.scheme}://{request.url.netloc}"
    download_url = f"{server_base}/api/packages/{item.id}/download?api_key={api_key}"
    config_line = ""
    if config_url:
        if item.platform.startswith("windows_"):
            config_line = f'Invoke-WebRequest -Uri "{config_url}" -OutFile "$FRP_DIR\\frpc.toml"\n'
        else:
            config_line = f'curl -sL "{config_url}" -o "$FRP_DIR/frpc.toml"\n'

    templates = _load_script_templates()
    template = templates.get(item.platform) or _default_template_for_platform(item.platform)
    script = (
        template.replace("{{filename}}", item.filename)
        .replace("{{download_url}}", download_url)
        .replace("{{install_path}}", install_path)
        .replace("{{config_line}}", config_line)
        .replace("{{platform}}", item.platform)
        .replace("{{version}}", item.version)
    )
    return PlainTextResponse(content=script)
