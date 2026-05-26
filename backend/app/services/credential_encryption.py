"""SSH 凭据加解密"""
import base64
import hashlib
import logging
from typing import Optional

from app.config import get_settings

logger = logging.getLogger(__name__)


def _encryption_key() -> bytes:
    settings = get_settings()
    secret = (settings.ssh_credential_secret or "").strip()
    if secret:
        return hashlib.sha256(secret.encode("utf-8")).digest()
    logger.warning(
        "SSH_CREDENTIAL_SECRET 未配置，使用基于认证配置的派生开发密钥（仅限开发环境）"
    )
    fallback = f"{settings.auth_username}:{settings.auth_password}:ssh-credential-dev"
    return hashlib.sha256(fallback.encode("utf-8")).digest()


def encrypt_secret(plain: Optional[str]) -> Optional[str]:
    if plain is None or plain == "":
        return None
    key = _encryption_key()
    data = plain.encode("utf-8")
    encrypted = bytes([data[i] ^ key[i % len(key)] for i in range(len(data))])
    return base64.b64encode(encrypted).decode("ascii")


def decrypt_secret(encrypted: Optional[str]) -> Optional[str]:
    if not encrypted:
        return None
    try:
        key = _encryption_key()
        data = base64.b64decode(encrypted.encode("ascii"))
        plain = bytes([data[i] ^ key[i % len(key)] for i in range(len(data))])
        return plain.decode("utf-8")
    except Exception:
        return None
