"""认证模块"""
import secrets
import base64
import hashlib
from typing import Annotated, Optional
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.models.user import User
from app.models.api_key import ApiKey

settings = get_settings()
security = HTTPBasic(auto_error=False)  # 不自动报错，避免浏览器弹窗
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码"""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """获取密码哈希"""
    return pwd_context.hash(password)


def authenticate_user(db: Session, username: str, password: str) -> User | None:
    """认证用户"""
    user = db.query(User).filter(User.username == username).first()
    if not user:
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user


def get_auth_from_header(authorization: Optional[str]) -> Optional[tuple[str, str]]:
    """从 Authorization header 中提取用户名和密码"""
    if not authorization:
        return None
    
    try:
        scheme, credentials = authorization.split(' ', 1)
        if scheme.lower() != 'basic':
            return None
        
        decoded = base64.b64decode(credentials).decode('utf-8')
        username, password = decoded.split(':', 1)
        return username, password
    except Exception:
        return None


def hash_api_key(key: str) -> str:
    """对 API Key 进行哈希"""
    return hashlib.sha256(key.encode()).hexdigest()


def verify_api_key(db: Session, api_key: str) -> Optional[ApiKey]:
    """验证 API Key"""
    key_hash = hash_api_key(api_key)
    api_key_obj = db.query(ApiKey).filter(ApiKey.key == key_hash).first()
    
    if not api_key_obj:
        return None
    
    # 检查是否激活
    if not api_key_obj.is_active:
        return None
    
    # 检查是否过期
    if api_key_obj.is_expired():
        return None
    
    # 更新最后使用时间
    from datetime import datetime
    api_key_obj.last_used_at = datetime.utcnow()
    db.commit()
    
    return api_key_obj


def get_current_user(
    request: Request,
    db: Session = Depends(get_db)
) -> User:
    """获取当前认证用户（支持 Basic Auth 和 API Key）"""
    # 从 Header 中获取 Authorization
    authorization = request.headers.get('Authorization')
    
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未提供认证信息",
        )
    
    # 尝试 API Key 认证（Bearer token）
    if authorization.startswith('Bearer '):
        api_key = authorization[7:].strip()
        api_key_obj = verify_api_key(db, api_key)
        if api_key_obj:
            # API Key 验证成功，返回一个临时用户对象
            # 使用 API Key 的描述作为用户名标识
            temp_user = User(
                id=-api_key_obj.id,  # 使用负数 ID 标识 API Key 用户
                username=f"api_key_{api_key_obj.id}",
                password_hash=""
            )
            return temp_user
        else:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="API Key 无效或已过期",
            )
    
    # 尝试 Basic Auth 认证
    auth_info = get_auth_from_header(authorization)
    if not auth_info:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="认证格式错误",
        )
    
    username, password = auth_info
    
    # 验证用户
    user = authenticate_user(db, username, password)
    
    if not user:
        # 如果数据库中没有用户，使用配置中的默认认证
        if (username == settings.auth_username and 
            password == settings.auth_password):
            # 返回一个临时用户对象（不保存到数据库）
            temp_user = User(
                id=0,
                username=username,
                password_hash=get_password_hash(password)
            )
            return temp_user
        
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
        )
    
    return user


def verify_credentials(credentials: HTTPBasicCredentials) -> bool:
    """简单验证凭据（用于兼容 frps 认证）"""
    correct_username = secrets.compare_digest(
        credentials.username.encode("utf8"),
        settings.auth_username.encode("utf8")
    )
    correct_password = secrets.compare_digest(
        credentials.password.encode("utf8"),
        settings.auth_password.encode("utf8")
    )
    return correct_username and correct_password

