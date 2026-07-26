"""Docker Engine API 凭据管理。"""
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models.docker_credential import DockerCredential
from app.models.managed_host import ManagedHost
from app.models.user import User
from app.schemas.managed_host import (
    DockerCredentialCreate,
    DockerCredentialResponse,
    DockerCredentialUpdate,
)
from app.services.credential_encryption import encrypt_secret
from app.services.host_access_service import require_admin

router = APIRouter(prefix="/api/docker-credentials", tags=["Docker 凭据"])


def _response(row: DockerCredential) -> DockerCredentialResponse:
    return DockerCredentialResponse(
        id=row.id,
        name=row.name,
        auth_type=row.auth_type,
        username=row.username,
        has_password=bool(row.password_encrypted),
        has_api_key=bool(row.api_key_encrypted),
        has_ca_cert=bool(row.ca_cert_encrypted),
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _validate(auth_type, username, password, api_key, existing=False):
    if auth_type == "password":
        if not username:
            raise HTTPException(status_code=400, detail="Portainer 密码认证需要用户名")
        if not existing and not password:
            raise HTTPException(status_code=400, detail="Portainer 密码认证需要密码")
    if auth_type == "api_key" and not existing and not api_key:
        raise HTTPException(status_code=400, detail="需要提供 Portainer API Key")


@router.get("", response_model=List[DockerCredentialResponse])
def list_credentials(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_admin(current_user)
    return [_response(row) for row in db.query(DockerCredential).order_by(DockerCredential.id.desc()).all()]


@router.post("", response_model=DockerCredentialResponse, status_code=201)
def create_credential(
    body: DockerCredentialCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_admin(current_user)
    _validate(
        body.auth_type, body.username, body.password, body.api_key
    )
    row = DockerCredential(
        name=body.name.strip(),
        auth_type=body.auth_type,
        username=body.username.strip() if body.username else None,
        password_encrypted=encrypt_secret(body.password),
        api_key_encrypted=encrypt_secret(body.api_key),
        ca_cert_encrypted=encrypt_secret(body.ca_cert),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _response(row)


@router.put("/{credential_id}", response_model=DockerCredentialResponse)
def update_credential(
    credential_id: int,
    body: DockerCredentialUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_admin(current_user)
    row = db.query(DockerCredential).filter(DockerCredential.id == credential_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Docker 凭据不存在")
    values = body.model_dump(exclude_unset=True)
    next_type = values.get("auth_type", row.auth_type)
    next_username = values.get("username", row.username)
    _validate(
        next_type,
        next_username,
        values.get("password"),
        values.get("api_key"),
        existing=True,
    )
    if next_type == "api_key":
        if "api_key" in values and not values["api_key"]:
            raise HTTPException(status_code=400, detail="Portainer API Key 不能为空")
        if not values.get("api_key") and not row.api_key_encrypted:
            raise HTTPException(status_code=400, detail="需要提供 Portainer API Key")
    if next_type == "password":
        if not next_username:
            raise HTTPException(status_code=400, detail="Portainer 密码认证需要用户名")
        if "password" in values and not values["password"]:
            raise HTTPException(status_code=400, detail="Portainer 密码不能为空")
        if not values.get("password") and not row.password_encrypted:
            raise HTTPException(status_code=400, detail="Portainer 密码认证需要密码")
    for plain_name, encrypted_name in (
        ("password", "password_encrypted"),
        ("api_key", "api_key_encrypted"),
        ("ca_cert", "ca_cert_encrypted"),
    ):
        if plain_name in values:
            setattr(row, encrypted_name, encrypt_secret(values.pop(plain_name)))
    for field, value in values.items():
        setattr(row, field, value.strip() if isinstance(value, str) else value)
    db.commit()
    db.refresh(row)
    return _response(row)


@router.delete("/{credential_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_credential(
    credential_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_admin(current_user)
    row = db.query(DockerCredential).filter(DockerCredential.id == credential_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Docker 凭据不存在")
    used = db.query(ManagedHost).filter(
        ManagedHost.docker_credential_id == credential_id
    ).count()
    if used:
        raise HTTPException(status_code=409, detail=f"该凭据正被 {used} 台 Docker 主机使用")
    db.delete(row)
    db.commit()
