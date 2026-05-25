"""Field-level encryption for sensitive DB values (H-07).

Uses Fernet symmetric encryption (AES-128-CBC + HMAC-SHA256).
The key is derived from ENCRYPTION_KEY env var via PBKDF2-HMAC-SHA256 so
the env var does not need to be a valid Fernet key itself.

Usage:
    from app.core.encryption import encrypt_field, decrypt_field

    ciphertext = encrypt_field("raw_token")   # returns None if key not set
    plaintext  = decrypt_field(ciphertext)    # returns None on failure
"""

import base64
import hashlib
import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)

_fernet = None


def _get_fernet():
    """Lazy-initialise a Fernet instance derived from ENCRYPTION_KEY."""
    global _fernet
    if _fernet is not None:
        return _fernet

    raw_key = os.getenv("ENCRYPTION_KEY", "")
    if not raw_key:
        return None

    try:
        from cryptography.fernet import Fernet

        # Derive a 32-byte key and base64url-encode it to produce a valid Fernet key
        derived = hashlib.pbkdf2_hmac(
            "sha256",
            raw_key.encode(),
            b"blissclip-field-encryption",
            iterations=100_000,
            dklen=32,
        )
        fernet_key = base64.urlsafe_b64encode(derived)
        _fernet = Fernet(fernet_key)
        return _fernet
    except Exception as exc:
        logger.warning("[encryption] Failed to initialise Fernet: %s", exc)
        return None


def encrypt_field(plaintext: Optional[str]) -> Optional[str]:
    """Encrypt a string value. Returns None when encryption is unavailable or input is None."""
    if plaintext is None:
        return None
    f = _get_fernet()
    if f is None:
        logger.debug("[encryption] ENCRYPTION_KEY not set — storing field unencrypted")
        return plaintext
    try:
        return f.encrypt(plaintext.encode()).decode()
    except Exception as exc:
        logger.error("[encryption] encrypt_field failed: %s", exc)
        return plaintext  # fail-open: store plaintext rather than lose the value


def decrypt_field(ciphertext: Optional[str]) -> Optional[str]:
    """Decrypt a value previously encrypted with encrypt_field. Returns None on failure."""
    if ciphertext is None:
        return None
    f = _get_fernet()
    if f is None:
        return ciphertext  # ENCRYPTION_KEY not set — value stored as plaintext
    try:
        return f.decrypt(ciphertext.encode()).decode()
    except Exception:
        # Value may be legacy plaintext — return as-is
        return ciphertext
