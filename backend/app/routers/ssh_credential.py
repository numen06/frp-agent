"""SSH 凭据管理路由"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models.user import User
from app.models.ssh_credential import SshCredential
from app.schemas.ssh_credential import (
    SshCredentialCreate,
    SshCredentialUpdate,
    SshCredentialResponse,
)
from app.services.credential_encryption import encrypt_secret

router = APIRouter(prefix="/api/ssh-credentials", tags=["SSH 凭据"])


def _to_response(cred: SshCredential) -> SshCredentialResponse:
    return SshCredentialResponse(
        id=cred.id,
        name=cred.name,
        username=cred.username,
        auth_type=cred.auth_type,
        has_password=bool(cred.password_encrypted),
        has_private_key=bool(cred.private_key_encrypted),
        has_passphrase=bool(cred.passphrase_encrypted),
        created_at=cred.created_at,
        updated_at=cred.updated_at,
    )


@router.get("", response_model=List[SshCredentialResponse])
def list_credentials(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    rows = db.query(SshCredential).order_by(SshCredential.id.desc()).all()
    return [_to_response(c) for c in rows]


@router.post("", response_model=SshCredentialResponse, status_code=status.HTTP_201_CREATED)
def create_credential(
    body: SshCredentialCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if body.auth_type == "password" and not body.password:
        raise HTTPException(status_code=400, detail="密码认证需要提供 password")
    if body.auth_type == "private_key" and not body.private_key:
        raise HTTPException(status_code=400, detail="私钥认证需要提供 private_key")

    cred = SshCredential(
        name=body.name,
        username=body.username,
        auth_type=body.auth_type,
        password_encrypted=encrypt_secret(body.password) if body.password else None,
        private_key_encrypted=encrypt_secret(body.private_key) if body.private_key else None,
        passphrase_encrypted=encrypt_secret(body.passphrase) if body.passphrase else None,
    )
    db.add(cred)
    db.commit()
    db.refresh(cred)
    return _to_response(cred)


@router.put("/{credential_id}", response_model=SshCredentialResponse)
def update_credential(
    credential_id: int,
    body: SshCredentialUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    cred = db.query(SshCredential).filter(SshCredential.id == credential_id).first()
    if not cred:
        raise HTTPException(status_code=404, detail="凭据不存在")

    if body.name is not None:
        cred.name = body.name
    if body.username is not None:
        cred.username = body.username
    if body.auth_type is not None:
        cred.auth_type = body.auth_type
    if body.password is not None:
        cred.password_encrypted = encrypt_secret(body.password) if body.password else None
    if body.private_key is not None:
        cred.private_key_encrypted = encrypt_secret(body.private_key) if body.private_key else None
    if body.passphrase is not None:
        cred.passphrase_encrypted = encrypt_secret(body.passphrase) if body.passphrase else None

    db.commit()
    db.refresh(cred)
    return _to_response(cred)


@router.delete("/{credential_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_credential(
    credential_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    cred = db.query(SshCredential).filter(SshCredential.id == credential_id).first()
    if not cred:
        raise HTTPException(status_code=404, detail="凭据不存在")
    db.delete(cred)
    db.commit()
