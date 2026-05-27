"""客户端升级任务查询"""
import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models.user import User
from app.models.client_upgrade_job import ClientUpgradeJob
from app.schemas.ssh_upgrade import ClientUpgradeJobResponse
from app.services.ssh_upgrade_service import refresh_detached_job_results

router = APIRouter(prefix="/api/client-upgrade", tags=["客户端升级"])


@router.get("/jobs/{job_id}", response_model=ClientUpgradeJobResponse)
def get_job(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    job = db.query(ClientUpgradeJob).filter(ClientUpgradeJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="任务不存在")
    return job


@router.get("/jobs/{job_id}/results")
def get_job_results(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    job = db.query(ClientUpgradeJob).filter(ClientUpgradeJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="任务不存在")
    results = refresh_detached_job_results(db, job)
    if not results and job.result_json:
        try:
            results = json.loads(job.result_json)
        except json.JSONDecodeError:
            results = []
    return {
        "job": ClientUpgradeJobResponse.model_validate(job),
        "results": results,
    }
