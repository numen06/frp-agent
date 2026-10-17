"""Encrypted NLA verifier, bound to the current platform password hash."""
import hmac
import json
import re

from passlib.hash import nthash

from app.services.credential_encryption import decrypt_secret, encrypt_secret


def ntlm_verifier(user):
    try:
        value = json.loads(decrypt_secret(user.rdp_ntlm_encrypted) or "{}")
        if (hmac.compare_digest(value.get("stamp", ""), user.password_hash)
                and re.fullmatch(r"[0-9a-f]{32}", value.get("hash", ""))):
            return value["hash"]
    except (ValueError, TypeError):
        pass
    return None


def remember_ntlm_password(db, user, password):
    if not ntlm_verifier(user):
        user.rdp_ntlm_encrypted = encrypt_secret(json.dumps({
            "stamp": user.password_hash, "hash": nthash.hash(password),
        }))
        db.commit()
