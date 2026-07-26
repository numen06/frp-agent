"""SSH 凭据加解密"""
import base64
import hashlib
import logging
import os
from typing import Optional

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

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
    nonce = os.urandom(12)
    encrypted = AESGCM(key).encrypt(nonce, plain.encode("utf-8"), b"frp-agent:ssh:v2")
    return "v2:" + base64.b64encode(nonce + encrypted).decode("ascii")


def decrypt_secret(encrypted: Optional[str]) -> Optional[str]:
    if not encrypted:
        return None
    try:
        key = _encryption_key()
        if encrypted.startswith("v2:"):
            payload = base64.b64decode(encrypted[3:].encode("ascii"))
            nonce, ciphertext = payload[:12], payload[12:]
            plain = AESGCM(key).decrypt(
                nonce, ciphertext, b"frp-agent:ssh:v2"
            )
            return plain.decode("utf-8")
        # 兼容升级前使用 XOR 保存的旧凭据；下次编辑时会自动写入 v2。
        data = base64.b64decode(encrypted.encode("ascii"))
        plain = bytes([data[i] ^ key[i % len(key)] for i in range(len(data))])
        return plain.decode("utf-8")
    except Exception:
        return None
