"""FRP 安装包管理路由"""
import json
import logging
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
from app.schemas.frp_package import (
    FrpPackageResponse,
    FrpPackagePaginatedResponse,
    FrpPackageSyncRequest,
    PackageSyncJobResponse,
    PackageSyncJobCreatedResponse,
)
from app.config import get_settings
from app.services.github_service import GithubService
from app.services.package_sync_service import (
    create_sync_job,
    create_finished_sync_job,
    schedule_sync_job,
    job_to_dict,
)
from app.models.package_sync_job import PackageSyncJob
from app.script_templates import load_shell_template

router = APIRouter(prefix="/api/packages", tags=["安装包管理"])
logger = logging.getLogger(__name__)

# 手动上传时的平台标识格式（与 GitHub 资源名中的平台段风格一致，不枚举具体值）
_UPLOAD_PLATFORM_PATTERN = re.compile(r"^[a-zA-Z0-9_]+$")

# 从官方 frp 安装包文件名自动解析版本和平台
# 例如: frp_0.61.1_linux_amd64.tar.gz -> version=v0.61.1, platform=linux_amd64
#       frp_0.61.1_windows_amd64.zip -> version=v0.61.1, platform=windows_amd64
_FRP_FILENAME_RE = re.compile(
    r"^frp_(\d+\.\d+\.\d+)_(.+)\.(?:tar\.gz|tgz|zip|tar\.xz)$",
    re.IGNORECASE,
)


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
    # 优先使用显式传入的 api_key（query/header），避免被登录态 Bearer token 覆盖。
    if not api_key:
        api_key = request.headers.get("X-API-Key")
    if not api_key and authorization.startswith("Bearer "):
        api_key = authorization[7:].strip()
    if not api_key:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="仅支持 API Key 认证")
    api_key_obj = verify_api_key(db, api_key)
    if not api_key_obj:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="API Key 无效或已过期")
    return api_key_obj


def _package_file_ready(item: FrpPackage) -> bool:
    if not item or not item.file_path:
        return False
    try:
        return os.path.isfile(item.file_path) and os.path.getsize(item.file_path) > 0
    except OSError:
        return False


def _ready_package_for(db: Session, version: str, platform: str) -> Optional[FrpPackage]:
    rows = (
        db.query(FrpPackage)
        .filter(
            FrpPackage.version == version,
            FrpPackage.platform == platform,
            FrpPackage.is_active == True,
        )
        .order_by(FrpPackage.downloaded_at.desc(), FrpPackage.id.desc())
        .all()
    )
    for row in rows:
        if _package_file_ready(row):
            return row
    return None


def _job_platforms(job: PackageSyncJob) -> List[str]:
    try:
        value = json.loads(job.platforms or "[]")
        return value if isinstance(value, list) else []
    except json.JSONDecodeError:
        return []


def _active_sync_jobs_for_version(db: Session, version: str) -> List[PackageSyncJob]:
    return (
        db.query(PackageSyncJob)
        .filter(
            PackageSyncJob.version == version,
            PackageSyncJob.status.in_(["queued", "running"]),
        )
        .order_by(PackageSyncJob.created_at.asc())
        .all()
    )


def _scripts_file_path() -> str:
    return os.path.join(_ensure_packages_dir(), "install_scripts.json")


def _platforms_cache_file_path() -> str:
    return os.path.join(_ensure_packages_dir(), "platforms_cache.json")


def _load_platforms_cache() -> dict:
    path = _platforms_cache_file_path()
    if not os.path.exists(path):
        return {"platforms": [], "version": None, "synced_at": None}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            if not isinstance(data, dict):
                return {"platforms": [], "version": None, "synced_at": None}
            return {
                "platforms": data.get("platforms") or [],
                "version": data.get("version"),
                "synced_at": data.get("synced_at"),
            }
    except Exception:
        return {"platforms": [], "version": None, "synced_at": None}


def _save_platforms_cache(platforms: List[str], version: Optional[str]) -> dict:
    payload = {
        "platforms": sorted(list({x for x in (platforms or []) if x})),
        "version": version,
        "synced_at": datetime.utcnow().isoformat(),
    }
    with open(_platforms_cache_file_path(), "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    return payload


def _versions_cache_file_path() -> str:
    return os.path.join(_ensure_packages_dir(), "versions_cache.json")


def _load_versions_cache() -> dict:
    path = _versions_cache_file_path()
    if not os.path.exists(path):
        return {"latest_version": None, "recent_versions": [], "synced_at": None}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            if not isinstance(data, dict):
                return {"latest_version": None, "recent_versions": [], "synced_at": None}
            return {
                "latest_version": data.get("latest_version"),
                "recent_versions": data.get("recent_versions") or [],
                "synced_at": data.get("synced_at"),
            }
    except Exception:
        return {"latest_version": None, "recent_versions": [], "synced_at": None}


def _save_versions_cache(latest: Optional[str], recent: List[str]) -> dict:
    payload = {
        "latest_version": latest,
        "recent_versions": [x for x in (recent or []) if x][:20],
        "synced_at": datetime.utcnow().isoformat(),
    }
    with open(_versions_cache_file_path(), "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    return payload


def _version_sort_key(tag: str):
    if not tag:
        return (0,)
    s = tag.strip().lstrip("vV")
    parts = []
    for part in re.split(r"[.\-]", s):
        if part.isdigit():
            parts.append(int(part))
        else:
            parts.append(0)
    return tuple(parts)


def _sort_versions_desc(versions: List[str]) -> List[str]:
    return sorted({x for x in versions if x}, key=_version_sort_key, reverse=True)


def _merge_versions_local_and_cache(db: Session, cache: dict) -> List[str]:
    rows = db.query(FrpPackage.version).distinct().all()
    local = [r[0] for r in rows if r[0]]
    all_v = set(local)
    for v in cache.get("recent_versions") or []:
        if v:
            all_v.add(v)
    lv = cache.get("latest_version")
    if lv:
        all_v.add(lv)
    return _sort_versions_desc(list(all_v))


def _refresh_versions_cache_from_releases(releases: List[dict]) -> dict:
    if not releases:
        return _load_versions_cache()
    latest = releases[0].get("tag_name")
    recent: List[str] = []
    for x in releases[:15]:
        tag = x.get("tag_name")
        if tag and tag not in recent:
            recent.append(tag)
    return _save_versions_cache(latest, recent)


def _merge_cached_with_local(db: Session, cached_platforms: List[str]) -> List[str]:
    local_rows = db.query(FrpPackage.platform).distinct().all()
    local_platforms = [r[0] for r in local_rows if r[0]]
    return _merge_platform_lists(cached_platforms, local_platforms)


def _default_template_for_platform(platform: str) -> str:
    if platform.startswith("windows_"):
        return load_shell_template("pkg_install_windows.ps1")
    return load_shell_template("pkg_install_linux.sh")


def _default_upgrade_template_for_platform(platform: str) -> str:
    if platform.startswith("windows_"):
        return load_shell_template("pkg_upgrade_windows.ps1")
    return load_shell_template("pkg_upgrade_linux.sh")


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


@router.get("", response_model=FrpPackagePaginatedResponse)
def list_packages(
    version: Optional[str] = Query(None),
    platform: Optional[str] = Query(None),
    source: Optional[str] = Query(None),
    page: int = Query(1, ge=1, description="页码，从 1 开始"),
    page_size: int = Query(10, ge=1, le=500, description="每页条数（列表页建议≤100；脚本弹窗可选更大 batch）"),
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
    total = query.count()
    offset = (page - 1) * page_size
    items = (
        query.order_by(FrpPackage.downloaded_at.desc())
        .offset(offset)
        .limit(page_size)
        .all()
    )
    return FrpPackagePaginatedResponse(
        items=[FrpPackageResponse.model_validate(p) for p in items],
        total=total,
        page=page,
        page_size=page_size,
    )


def _parse_filename_info(filename: str) -> Optional[dict]:
    """从官方 frp 安装包文件名解析版本号和平台标识。"""
    if not filename:
        return None
    m = _FRP_FILENAME_RE.match(filename.strip())
    if not m:
        return None
    return {"version": f"v{m.group(1)}", "platform": m.group(2)}


def _normalize_optional_form(value: Optional[str]) -> Optional[str]:
    """multipart 里空串应视为未填，避免仅含空格被当成有效值。"""
    if value is None:
        return None
    s = value.strip()
    return s if s else None


def _safe_package_basename(name: str) -> str:
    """仅保留文件名，去掉路径与非法字符（Windows/Unix）。"""
    base = os.path.basename((name or "").replace("\\", "/").strip()) or "package.bin"
    base = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", base)
    if len(base) > 220:
        base = base[:220]
    return base


@router.post("/upload", response_model=FrpPackageResponse)
async def upload_package(
    package_file: UploadFile = File(...),
    version: Optional[str] = Form(default=None),
    platform: Optional[str] = Form(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """单文件上传（保留兼容）。"""
    result = await _do_upload_package(package_file, version, platform, db)
    return result


async def _do_upload_package(
    package_file: UploadFile,
    version: Optional[str],
    platform: Optional[str],
    db: Session,
) -> FrpPackage:
    # File 必须声明在 Form 之前，否则部分环境下 multipart 解析会异常（FastAPI 官方建议）
    version = _normalize_optional_form(version)
    platform = _normalize_optional_form(platform)

    raw_upload_name = (package_file.filename or "").strip()
    filename: Optional[str] = _safe_package_basename(raw_upload_name) if raw_upload_name else None

    # 尝试从文件名自动解析
    parsed = _parse_filename_info(filename or "")
    if parsed:
        if not version:
            version = parsed["version"]
        if not platform:
            platform = parsed["platform"]

    if not version or not platform:
        raise HTTPException(
            status_code=400,
            detail="无法从文件名自动解析版本号和平台，请手动填写。文件名格式应为 frp_版本_平台.扩展名（如 frp_0.61.1_linux_amd64.tar.gz）",
        )

    if not _UPLOAD_PLATFORM_PATTERN.match(platform or ""):
        raise HTTPException(
            status_code=400,
            detail="平台标识格式无效，请使用与官方发布包一致的平台名（如 linux_amd64），仅字母数字下划线",
        )

    packages_dir = _ensure_packages_dir()
    if filename is None:
        filename = f"frp_{version}_{platform}.bin"
    target_name = f"{version}_{platform}_{filename}"
    save_path = os.path.join(packages_dir, target_name)

    try:
        with open(save_path, "wb") as f:
            content = await package_file.read()
            f.write(content)
    except OSError as e:
        logger.exception("写入安装包文件失败: %s", save_path)
        raise HTTPException(
            status_code=500,
            detail=f"无法写入安装包文件（请检查 data/packages 目录权限与磁盘空间）: {e}",
        ) from e

    def _upload_path_key(p: Optional[str]) -> str:
        if not p:
            return ""
        try:
            return os.path.normcase(os.path.normpath(os.path.abspath(p)))
        except OSError:
            return os.path.normpath(p or "")

    save_key = _upload_path_key(save_path)
    keeper = None
    try:
        service = GithubService()
        checksum = service.calculate_sha256(save_path)
        size = os.path.getsize(save_path)

        existing_rows = (
            db.query(FrpPackage)
            .filter(FrpPackage.version == version, FrpPackage.platform == platform)
            .order_by(FrpPackage.id.asc())
            .all()
        )

        # 重名（同版本+同平台）一律覆盖：合并重复行，磁盘上新文件已写入 save_path
        for row in existing_rows:
            if row.file_path and _upload_path_key(row.file_path) == save_key:
                keeper = row
                break
        if keeper is None and existing_rows:
            keeper = existing_rows[0]

        for row in existing_rows:
            if keeper and row.id == keeper.id:
                continue
            if row.file_path and os.path.exists(row.file_path) and _upload_path_key(row.file_path) != save_key:
                try:
                    os.remove(row.file_path)
                except OSError as rm_err:
                    logger.warning("删除重复安装包文件失败: %s", rm_err)
            db.delete(row)

        if keeper:
            if keeper.file_path and os.path.exists(keeper.file_path) and _upload_path_key(keeper.file_path) != save_key:
                try:
                    os.remove(keeper.file_path)
                except OSError as rm_err:
                    logger.warning("删除旧安装包文件失败（可忽略）: %s", rm_err)
            keeper.filename = filename
            keeper.file_path = save_path
            keeper.file_size = size
            keeper.source = "upload"
            keeper.download_url = None
            keeper.sha256_checksum = checksum
            keeper.downloaded_at = datetime.utcnow()
            db.commit()
            db.refresh(keeper)
            return keeper

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
    except Exception as e:
        logger.exception("保存安装包记录失败")
        db.rollback()
        same_path_as_existing = (
            keeper is not None
            and keeper.file_path
            and _upload_path_key(keeper.file_path) == save_key
        )
        if os.path.exists(save_path) and not same_path_as_existing:
            try:
                os.remove(save_path)
            except OSError:
                pass
        raise HTTPException(
            status_code=500,
            detail=f"保存安装包失败: {e}",
        ) from e


@router.post("/upload/batch")
async def upload_package_batch(
    package_files: List[UploadFile] = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """批量上传安装包，每个文件必须能从文件名自动解析版本和平台。"""
    if not package_files:
        raise HTTPException(status_code=400, detail="未选择任何文件")

    results = []
    errors = []
    for idx, package_file in enumerate(package_files):
        try:
            item = await _do_upload_package(package_file, None, None, db)
            results.append({"index": idx, "filename": package_file.filename, "success": True, "item": item})
        except HTTPException as exc:
            errors.append({"index": idx, "filename": package_file.filename, "detail": exc.detail})
        except Exception as exc:
            logger.exception("批量上传第 %d 个文件失败: %s", idx, package_file.filename)
            errors.append({"index": idx, "filename": package_file.filename, "detail": str(exc)})

    return {
        "total": len(package_files),
        "success_count": len(results),
        "fail_count": len(errors),
        "items": results,
        "errors": errors,
    }


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
def get_supported_platforms(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # 只返回后台缓存 + 本地平台，不主动请求 GitHub
    cache = _load_platforms_cache()
    merged = _merge_cached_with_local(db, cache.get("platforms") or [])
    return {
        "platforms": merged,
        "version": cache.get("version"),
        "synced_at": cache.get("synced_at"),
        "source": "backend-cache",
    }


@router.get("/versions")
def get_supported_versions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """与 platforms 类似：合并 GitHub 同步缓存与本地库中的版本；提供最新与最近若干版本。"""
    cache = _load_versions_cache()
    merged = _merge_versions_local_and_cache(db, cache)
    latest = cache.get("latest_version") or (merged[0] if merged else None)
    recent = [v for v in (cache.get("recent_versions") or []) if v in set(merged)]
    if not recent and merged:
        recent = merged[:10]
    return {
        "versions": merged,
        "latest_version": latest,
        "recent_versions": recent,
        "synced_at": cache.get("synced_at"),
        "source": "backend-cache",
    }


@router.post("/platforms/sync")
async def sync_supported_platforms(
    version: Optional[str] = Query(None, description="可选，指定 release tag，不传则同步最新 release"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = GithubService()
    releases = await service.fetch_releases()
    if not releases:
        raise HTTPException(status_code=400, detail="GitHub 无可用 release")

    tag = version or releases[0].get("tag_name")
    release = next((x for x in releases if x.get("tag_name") == tag), None)
    if not release:
        raise HTTPException(status_code=404, detail="未找到指定版本 release")

    discovered = service.discover_platforms_from_release(release)
    saved = _save_platforms_cache(discovered, tag)
    _refresh_versions_cache_from_releases(releases)
    merged = _merge_cached_with_local(db, saved.get("platforms") or [])
    return {
        "platforms": merged,
        "version": saved.get("version"),
        "synced_at": saved.get("synced_at"),
        "source": "backend-cache",
    }


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


@router.post("/sync", response_model=PackageSyncJobCreatedResponse)
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

    ready_packages = {
        platform: pkg
        for platform in selected_platforms
        if (pkg := _ready_package_for(db, payload.version, platform)) is not None
    }
    active_by_platform = {}
    for active_job in _active_sync_jobs_for_version(db, payload.version):
        for platform in _job_platforms(active_job):
            if platform in selected_platforms and platform not in ready_packages:
                active_by_platform.setdefault(platform, active_job)

    downloadable_platforms = [
        platform
        for platform in selected_platforms
        if platform not in ready_packages and platform not in active_by_platform
    ]

    assets = release.get("assets", [])
    pending_assets = []
    for asset in assets:
        name = asset.get("name", "")
        platform = service.parse_platform_from_filename(name)
        if not platform or platform not in downloadable_platforms:
            continue
        source_url = asset.get("browser_download_url")
        if not source_url:
            continue
        pending_assets.append(
            {
                "name": name,
                "platform": platform,
                "source_url": source_url,
            }
        )

    if not pending_assets:
        if active_by_platform:
            job = next(iter(active_by_platform.values()))
            return PackageSyncJobCreatedResponse(
                job_id=job.job_id,
                status=job.status,
                total=job.total,
                completed=job.completed,
                message="相同版本/平台的同步任务正在进行中，已返回现有任务",
            )
        if ready_packages:
            results = [
                {
                    "platform": platform,
                    "filename": ready_packages[platform].filename,
                    "status": "skipped",
                    "message": "安装包已存在且文件可用，跳过下载",
                    "package_id": ready_packages[platform].id,
                }
                for platform in selected_platforms
                if platform in ready_packages
            ]
            job = create_finished_sync_job(
                db,
                payload.version,
                selected_platforms,
                payload.download_source,
                results,
            )
            return PackageSyncJobCreatedResponse(
                job_id=job.job_id,
                status=job.status,
                total=job.total,
                completed=job.completed,
                message="所选安装包已存在且文件可用，已跳过下载",
            )
        raise HTTPException(status_code=400, detail="未找到可下载的安装包资源")

    job = create_sync_job(
        db,
        payload.version,
        [asset["platform"] for asset in pending_assets],
        payload.download_source,
        pending_assets,
    )
    schedule_sync_job(job.job_id, pending_assets, sorted(discovered))
    skipped_count = len(selected_platforms) - len(pending_assets)
    message = "同步任务已创建，正在后台下载"
    if skipped_count > 0:
        message += f"（已跳过 {skipped_count} 个已存在或正在同步的平台）"
    return PackageSyncJobCreatedResponse(
        job_id=job.job_id,
        status=job.status,
        total=job.total,
        completed=job.completed,
        message=message,
    )


@router.get("/jobs/{job_id}", response_model=PackageSyncJobResponse)
def get_sync_job(
    job_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    job = db.query(PackageSyncJob).filter(PackageSyncJob.job_id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="同步任务不存在")
    return PackageSyncJobResponse.model_validate(job_to_dict(job))


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
    if not _package_file_ready(item):
        raise HTTPException(status_code=404, detail="安装包文件不存在")
    return FileResponse(path=item.file_path, filename=item.filename, media_type="application/octet-stream")


def _auth_for_install_script(request: Request, db: Session = Depends(get_db)):
    """install-script 端点的认证：支持 API Key 或已登录用户。
    用于 curl | bash 场景（传 api_key query param）以及前端已登录用户操作。"""
    # 优先尝试 API Key（query / header / Bearer）
    api_key = request.query_params.get("api_key")
    if not api_key:
        api_key = request.headers.get("X-API-Key")
    if not api_key:
        authorization = request.headers.get("Authorization", "")
        if authorization.startswith("Bearer "):
            api_key = authorization[7:].strip()
    if api_key:
        obj = verify_api_key(db, api_key)
        if obj:
            return {"type": "api_key", "obj": obj, "key": api_key}
    # 兜底使用统一登录认证逻辑（与其它受保护接口保持一致）
    try:
        user = get_current_user(request, db)
        return {"type": "user", "obj": user, "key": None}
    except HTTPException:
        pass
    raise HTTPException(status_code=401, detail="认证失败，请提供有效的 API Key 或登录凭证")


@router.get("/install-script")
def get_install_script(
    package_id: int = Query(..., ge=1),
    install_path: str = Query("/opt/frp"),
    config_url: Optional[str] = Query(None),
    request: Request = None,
    db: Session = Depends(get_db),
    auth_info: dict = Depends(_auth_for_install_script),
):
    item = db.query(FrpPackage).filter(FrpPackage.id == package_id, FrpPackage.is_active == True).first()
    if not item:
        raise HTTPException(status_code=404, detail="安装包不存在")
    if not _package_file_ready(item):
        raise HTTPException(status_code=404, detail="安装包文件尚未准备好，请等待同步完成或重新同步")

    api_key = request.query_params.get("api_key") or ""
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
    return PlainTextResponse(content=script, media_type="text/plain; charset=utf-8")


@router.get("/upgrade-script")
def get_upgrade_script(
    package_id: int = Query(..., ge=1),
    install_path: str = Query("/opt/frp"),
    request: Request = None,
    db: Session = Depends(get_db),
    auth_info: dict = Depends(_auth_for_install_script),
):
    item = db.query(FrpPackage).filter(FrpPackage.id == package_id, FrpPackage.is_active == True).first()
    if not item:
        raise HTTPException(status_code=404, detail="安装包不存在")
    if not _package_file_ready(item):
        raise HTTPException(status_code=404, detail="安装包文件尚未准备好，请等待同步完成或重新同步")

    api_key = request.query_params.get("api_key") or ""
    server_base = f"{request.url.scheme}://{request.url.netloc}"
    download_url = f"{server_base}/api/packages/{item.id}/download?api_key={api_key}"

    templates = _load_script_templates()
    upgrade_key = f"{item.platform}_upgrade"
    template = templates.get(upgrade_key) or _default_upgrade_template_for_platform(item.platform)
    script = (
        template.replace("{{filename}}", item.filename)
        .replace("{{download_url}}", download_url)
        .replace("{{install_path}}", install_path)
        .replace("{{platform}}", item.platform)
        .replace("{{version}}", item.version)
    )
    return PlainTextResponse(content=script, media_type="text/plain; charset=utf-8")
