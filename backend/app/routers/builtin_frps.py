"""内置 FRP 的配置、运行状态与首次登录提示，仅管理员可用。"""
from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.builtin_frps import BuiltinFrpsUpdate, BuiltinFrpsRawUpdate
from app.services.builtin_frps_service import builtin_frps_service, get_builtin_config, runtime_config
from app.services.credential_encryption import decrypt_secret, encrypt_secret
from app.services.host_access_service import require_admin

router = APIRouter(prefix="/api/builtin-frps", tags=["内置 FRP"])


@router.get("")
def get_status(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    require_admin(user)
    return builtin_frps_service.status(db)


@router.put("")
def configure(body: BuiltinFrpsUpdate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    require_admin(user)
    try:
        return builtin_frps_service.apply(db, body)
    except (ValueError, OSError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/restart")
def restart(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    require_admin(user)
    config = get_builtin_config(db)
    if not config.enabled:
        raise HTTPException(status_code=400, detail="请先保存并启用内置 FRP")
    raw = builtin_frps_service.raw_document(db)
    return save_raw_config(BuiltinFrpsRawUpdate(enabled=True, public_addr=config.public_addr,
                                             content=raw["content"], revision=raw["revision"]), db, user)


@router.get("/raw-config")
def get_raw_config(response: Response, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    require_admin(user)
    response.headers["Cache-Control"] = "no-store"
    try:
        return builtin_frps_service.raw_document(db)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/raw-config/preview")
def preview_raw_config(body: BuiltinFrpsUpdate, response: Response, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    require_admin(user)
    response.headers["Cache-Control"] = "no-store"
    try:
        return builtin_frps_service.raw_document(db, body)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/raw-config/validate")
def validate_raw_config(body: BuiltinFrpsRawUpdate, user: User = Depends(get_current_user)):
    require_admin(user)
    try:
        return builtin_frps_service.validate_raw(body)
    except (ValueError, OSError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.put("/raw-config")
def save_raw_config(body: BuiltinFrpsRawUpdate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    require_admin(user)
    try:
        return builtin_frps_service.apply(db, body)
    except (ValueError, OSError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/onboarding-seen")
def acknowledge_onboarding(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    require_admin(user)
    config = get_builtin_config(db)
    config.onboarding_seen = True
    db.commit()
    return {"success": True}


@router.post("/token")
def reveal_token(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    require_admin(user)
    config = get_builtin_config(db)
    if not config.token_encrypted:
        config.token_encrypted = encrypt_secret(runtime_config(config)["auth_token"])
        db.commit()
    token = decrypt_secret(config.token_encrypted)
    if not token:
        raise HTTPException(status_code=409, detail="FRP Token 无法解密，请检查 SSH_CREDENTIAL_SECRET")
    return {"auth_token": token}
