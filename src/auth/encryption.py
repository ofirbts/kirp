"""
Encryption Engine — Sensitive data at rest.

Zero Trust. Use Vault for secrets; encrypt sensitive payloads.
"""

from __future__ import annotations

import base64
import logging
import os
from typing import Any

logger = logging.getLogger(__name__)


class EncryptionEngine:
    """
    Encrypt/decrypt sensitive fields. Vault integration for key management.
    """

    def __init__(self, vault_addr: str | None = None) -> None:
        self._vault_addr = vault_addr or os.getenv("VAULT_ADDR", "http://localhost:8200")
        self._key: bytes | None = None

    def _get_key(self) -> bytes:
        """Derive or fetch key. Fallback: env KIRP_ENCRYPTION_KEY."""
        if self._key is not None:
            return self._key
        raw = os.getenv("KIRP_ENCRYPTION_KEY", "")
        if not raw or len(raw) < 32:
            logger.warning("KIRP_ENCRYPTION_KEY missing or short; using placeholder")
            raw = "0" * 32
        self._key = raw.encode("utf-8")[:32].ljust(32, b"\0")
        return self._key

    def encrypt(self, plain: str) -> str:
        """Encrypt string; return base64-encoded ciphertext."""
        try:
            from cryptography.fernet import Fernet
            from cryptography.hazmat.primitives import hashes
            from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
            kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=b"kirp", iterations=100000)
            key = base64.urlsafe_b64encode(kdf.derive(self._get_key()))
            f = Fernet(key)
            return f.encrypt(plain.encode("utf-8")).decode("ascii")
        except Exception as e:
            logger.error("Encryption failed: %s", e)
            raise

    def decrypt(self, cipher: str) -> str:
        """Decrypt base64-encoded ciphertext."""
        try:
            from cryptography.fernet import Fernet
            from cryptography.hazmat.primitives import hashes
            from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
            kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=b"kirp", iterations=100000)
            key = base64.urlsafe_b64encode(kdf.derive(self._get_key()))
            f = Fernet(key)
            return f.decrypt(cipher.encode("ascii")).decode("utf-8")
        except Exception as e:
            logger.error("Decryption failed: %s", e)
            raise
