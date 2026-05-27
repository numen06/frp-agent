"""GitHub 安装包后台同步服务"""
import asyncio
import json
import logging
import os
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.frp_package import FrpPackage
from app.models.package_sync_job import PackageSyncJob
from app.services.github_service import GithubService

logger = logging.getLogger(__name__)


def _ensure_packages_dir() -> str:
    from app.routers.frp_package import _ensure_packages_dir as ensure_dir

    return ensure_dir()


def _save_platforms_cache(platforms: List[str], version: str) -> dict:
    from app.routers.frp_package import _save_platforms_cache

    return _save_platforms_cache(platforms, version)


def _refresh_versions_cache_from_releases(releases: List[dict]) -> dict:
    from app.routers.frp_package import _refresh_versions_cache_from_releases

    return _refresh_versions_cache_from_releases(releases)


def create_sync_job(
    db: Session,
    version: str,
    platforms: List[str],
    download_source: str,
    pending_assets: List[Dict[str, str]],
) -> PackageSyncJob:
    job = PackageSyncJob(
        job_id=str(uuid.uuid4()),
        status="queued",
        version=version,
        platforms=json.dumps(platforms, ensure_ascii=False),
        download_source=download_source,
        total=len(pending_assets),
        completed=0,
        results=json.dumps([], ensure_ascii=False),
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def _update_job_progress(
    db: Session,
    job: PackageSyncJob,
    completed: int,
    results: List[dict],
):
    job.completed = completed
    job.results = json.dumps(results, ensure_ascii=False)
    job.updated_at = datetime.utcnow()
    db.commit()


def _finish_job(
    db: Session,
    job: PackageSyncJob,
    status: str,
    results: List[dict],
    error: Optional[str] = None,
):
    job.status = status
    job.completed = len(results)
    job.results = json.dumps(results, ensure_ascii=False)
    job.error = error
    job.finished_at = datetime.utcnow()
    job.updated_at = datetime.utcnow()
    db.commit()


async def _download_one_asset(
    service: GithubService,
    asset: Dict[str, str],
    download_source: str,
    version: str,
    packages_dir: str,
    db: Session,
) -> dict:
    name = asset["name"]
    platform = asset["platform"]
    source_url = asset["source_url"]
    download_urls = (
        service.build_accelerated_download_urls(source_url)
        if download_source == "accelerated"
        else [source_url]
    )
    save_path = os.path.join(packages_dir, name)
    try:
        attempt_errors: List[str] = []
        size = 0
        for download_url in download_urls:
            try:
                if os.path.exists(save_path):
                    os.remove(save_path)
                size = await service.download_asset(download_url, save_path)
                break
            except Exception as e:
                logger.warning("download failed for %s via %s: %s", name, download_url, e)
                attempt_errors.append(f"{download_url}: {e}")
                if os.path.exists(save_path):
                    try:
                        os.remove(save_path)
                    except OSError:
                        pass
        else:
            raise RuntimeError("; ".join(attempt_errors))
        checksum = service.calculate_sha256(save_path)

        existed = (
            db.query(FrpPackage)
            .filter(FrpPackage.version == version, FrpPackage.platform == platform)
            .first()
        )
        if existed:
            if os.path.exists(existed.file_path) and existed.file_path != save_path:
                os.remove(existed.file_path)
            existed.filename = name
            existed.file_path = save_path
            existed.file_size = size
            existed.source = "github"
            existed.download_url = source_url
            existed.sha256_checksum = checksum
            existed.downloaded_at = datetime.utcnow()
            db.commit()
            db.refresh(existed)
            package_id = existed.id
        else:
            item = FrpPackage(
                version=version,
                platform=platform,
                filename=name,
                file_path=save_path,
                file_size=size,
                source="github",
                download_url=source_url,
                is_active=True,
                sha256_checksum=checksum,
                downloaded_at=datetime.utcnow(),
            )
            db.add(item)
            db.commit()
            db.refresh(item)
            package_id = item.id

        return {
            "platform": platform,
            "filename": name,
            "status": "success",
            "message": "下载成功",
            "package_id": package_id,
        }
    except Exception as e:
        logger.exception("下载安装包失败: %s", name)
        if os.path.exists(save_path):
            try:
                os.remove(save_path)
            except OSError:
                pass
        return {
            "platform": platform,
            "filename": name,
            "status": "failed",
            "message": str(e),
        }


async def run_sync_job(job_uuid: str, pending_assets: List[Dict[str, str]], discovered_platforms: List[str]):
    """后台执行 GitHub 安装包同步任务。"""
    db = SessionLocal()
    try:
        job = db.query(PackageSyncJob).filter(PackageSyncJob.job_id == job_uuid).first()
        if not job:
            logger.error("同步任务不存在: %s", job_uuid)
            return

        job.status = "running"
        job.started_at = datetime.utcnow()
        job.updated_at = datetime.utcnow()
        db.commit()

        service = GithubService()
        packages_dir = _ensure_packages_dir()
        results: List[dict] = []
        success_count = 0

        for idx, asset in enumerate(pending_assets, start=1):
            result = await _download_one_asset(
                service,
                asset,
                job.download_source,
                job.version,
                packages_dir,
                db,
            )
            results.append(result)
            if result.get("status") == "success":
                success_count += 1
            _update_job_progress(db, job, idx, results)

        try:
            releases = await service.fetch_releases()
            _save_platforms_cache(discovered_platforms, job.version)
            _refresh_versions_cache_from_releases(releases)
        except Exception as e:
            logger.warning("同步完成后更新缓存失败: %s", e)

        if success_count == 0 and pending_assets:
            _finish_job(db, job, "failed", results, error="所有平台下载均失败")
        elif success_count < len(pending_assets):
            _finish_job(
                db,
                job,
                "completed",
                results,
                error=f"部分平台下载失败（成功 {success_count}/{len(pending_assets)}）",
            )
        else:
            _finish_job(db, job, "completed", results)
    except Exception as e:
        logger.exception("同步任务执行异常: %s", job_uuid)
        try:
            job = db.query(PackageSyncJob).filter(PackageSyncJob.job_id == job_uuid).first()
            if job:
                _finish_job(db, job, "failed", json.loads(job.results or "[]"), error=str(e))
        except Exception:
            logger.exception("更新失败任务状态时出错")
    finally:
        db.close()


def schedule_sync_job(job_uuid: str, pending_assets: List[Dict[str, str]], discovered_platforms: List[str]):
    """在事件循环中调度后台同步任务。"""
    asyncio.create_task(run_sync_job(job_uuid, pending_assets, discovered_platforms))


def job_to_dict(job: PackageSyncJob) -> Dict[str, Any]:
    results = []
    platforms = []
    if job.results:
        try:
            results = json.loads(job.results)
        except json.JSONDecodeError:
            results = []
    if job.platforms:
        try:
            platforms = json.loads(job.platforms)
        except json.JSONDecodeError:
            platforms = []
    return {
        "job_id": job.job_id,
        "status": job.status,
        "version": job.version,
        "platforms": platforms,
        "download_source": job.download_source,
        "total": job.total,
        "completed": job.completed,
        "results": results,
        "error": job.error,
        "created_at": job.created_at,
        "updated_at": job.updated_at,
        "started_at": job.started_at,
        "finished_at": job.finished_at,
    }
