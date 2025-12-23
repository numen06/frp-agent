"""API Key 管理路由"""
import secrets
import hashlib
import base64
from datetime import datetime, timedelta
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.models.user import User
from app.models.api_key import ApiKey
from app.schemas.api_key import (
    ApiKeyCreate,
    ApiKeyResponse,
    ApiKeyCreateResponse,
    ApiKeyUpdate
)
from app.database import get_db
from app.config import get_settings

router = APIRouter(prefix="/api/api-keys", tags=["API Key 管理"])


def generate_api_key() -> str:
    """生成 API Key（32字节，64字符）"""
    return secrets.token_urlsafe(32)


def hash_api_key(key: str) -> str:
    """对 API Key 进行哈希"""
    return hashlib.sha256(key.encode()).hexdigest()


def mask_api_key(key: str) -> str:
    """掩码 API Key（只显示前8位和后4位）"""
    if len(key) < 12:
        return "*" * len(key)
    return f"{key[:8]}...{key[-4:]}"


def encrypt_key(key: str) -> str:
    """加密 API Key（使用 base64 编码，简单但足够）"""
    # 使用应用密钥作为盐值
    settings = get_settings()
    salt = f"{settings.auth_username}{settings.auth_password}".encode()
    # 简单的 XOR 加密 + base64 编码
    encoded = base64.b64encode(bytes([ord(c) ^ salt[i % len(salt)] for i, c in enumerate(key)])).decode()
    return encoded


def decrypt_key(encrypted_key: str) -> Optional[str]:
    """解密 API Key"""
    try:
        settings = get_settings()
        salt = f"{settings.auth_username}{settings.auth_password}".encode()
        decoded = base64.b64decode(encrypted_key.encode())
        decrypted = ''.join([chr(decoded[i] ^ salt[i % len(salt)]) for i in range(len(decoded))])
        return decrypted
    except Exception:
        return None


@router.post("", response_model=ApiKeyCreateResponse, status_code=status.HTTP_201_CREATED)
def create_api_key(
    api_key_data: ApiKeyCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """创建新的 API Key"""
    # 生成密钥
    raw_key = generate_api_key()
    key_hash = hash_api_key(raw_key)
    
    # 检查哈希是否已存在（极小概率）
    existing = db.query(ApiKey).filter(ApiKey.key == key_hash).first()
    if existing:
        # 如果冲突，重新生成
        raw_key = generate_api_key()
        key_hash = hash_api_key(raw_key)
    
    # 创建 API Key 记录
    # 加密存储原始密钥（用于后续获取）
    encrypted_key = encrypt_key(raw_key)
    api_key = ApiKey(
        key=key_hash,
        key_encrypted=encrypted_key,  # 存储加密后的原始密钥
        description=api_key_data.description,
        expires_at=api_key_data.expires_at,
        is_active=True
    )
    
    db.add(api_key)
    db.commit()
    db.refresh(api_key)
    
    return ApiKeyCreateResponse(
        id=api_key.id,
        key=raw_key,  # 返回原始密钥
        description=api_key.description,
        expires_at=api_key.expires_at,
        is_active=api_key.is_active,
        created_at=api_key.created_at
    )


@router.get("", response_model=List[ApiKeyResponse])
def list_api_keys(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取 API Key 列表"""
    api_keys = db.query(ApiKey).order_by(ApiKey.created_at.desc()).offset(skip).limit(limit).all()
    
    result = []
    for api_key in api_keys:
        # 使用掩码显示密钥
        masked_key = mask_api_key(api_key.key)
        result.append(ApiKeyResponse(
            id=api_key.id,
            key=masked_key,
            description=api_key.description,
            expires_at=api_key.expires_at,
            is_active=api_key.is_active,
            created_at=api_key.created_at,
            last_used_at=api_key.last_used_at,
            is_expired=api_key.is_expired()
        ))
    
    return result


@router.get("/{api_key_id}", response_model=ApiKeyResponse)
def get_api_key(
    api_key_id: int,
    include_full_key: bool = Query(False, description="是否返回完整密钥（仅用于前端显示）"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取单个 API Key 详情"""
    api_key = db.query(ApiKey).filter(ApiKey.id == api_key_id).first()
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API Key 不存在"
        )
    
    # 如果需要返回完整密钥，尝试解密
    if include_full_key and api_key.key_encrypted:
        full_key = decrypt_key(api_key.key_encrypted)
        if full_key:
            return ApiKeyResponse(
                id=api_key.id,
                key=full_key,  # 返回完整密钥
                description=api_key.description,
                expires_at=api_key.expires_at,
                is_active=api_key.is_active,
                created_at=api_key.created_at,
                last_used_at=api_key.last_used_at,
                is_expired=api_key.is_expired()
            )
    
    # 否则返回掩码后的密钥
    masked_key = mask_api_key(api_key.key)
    return ApiKeyResponse(
        id=api_key.id,
        key=masked_key,
        description=api_key.description,
        expires_at=api_key.expires_at,
        is_active=api_key.is_active,
        created_at=api_key.created_at,
        last_used_at=api_key.last_used_at,
        is_expired=api_key.is_expired()
    )


@router.put("/{api_key_id}", response_model=ApiKeyResponse)
def update_api_key(
    api_key_id: int,
    api_key_data: ApiKeyUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """更新 API Key"""
    api_key = db.query(ApiKey).filter(ApiKey.id == api_key_id).first()
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API Key 不存在"
        )
    
    # 更新字段
    if api_key_data.description is not None:
        if not api_key_data.description.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="描述不能为空"
            )
        api_key.description = api_key_data.description.strip()
    
    if api_key_data.expires_at is not None:
        api_key.expires_at = api_key_data.expires_at
    
    if api_key_data.is_active is not None:
        api_key.is_active = api_key_data.is_active
    
    db.commit()
    db.refresh(api_key)
    
    masked_key = mask_api_key(api_key.key)
    return ApiKeyResponse(
        id=api_key.id,
        key=masked_key,
        description=api_key.description,
        expires_at=api_key.expires_at,
        is_active=api_key.is_active,
        created_at=api_key.created_at,
        last_used_at=api_key.last_used_at,
        is_expired=api_key.is_expired()
    )


@router.delete("/{api_key_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_api_key(
    api_key_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """删除 API Key"""
    api_key = db.query(ApiKey).filter(ApiKey.id == api_key_id).first()
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API Key 不存在"
        )
    
    db.delete(api_key)
    db.commit()
    
    return None

