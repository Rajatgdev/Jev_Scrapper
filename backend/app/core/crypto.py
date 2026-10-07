"""Encrypt/decrypt user-provided API keys with Fernet (authenticated AES).

The master key(s) live in the ENCRYPTION_KEY env var (Railway backend + cron
services only) — never in the database, Git, or the frontend. Neon stores only
ciphertext. MultiFernet lets us rotate the master key later: put the NEW key
first, keep old keys after it (comma-separated), re-encrypt rows, then drop old.

Fail loud if ENCRYPTION_KEY is missing — never silently store plaintext.
"""
import os
from cryptography.fernet import Fernet, MultiFernet

CRYPTO_VERSION = "fernet-v1"


def _build() -> MultiFernet:
    raw = os.environ.get("ENCRYPTION_KEY", "").strip()
    if not raw:
        raise RuntimeError(
            "ENCRYPTION_KEY is not set — cannot encrypt/decrypt user keys. "
            "Generate one with: "
            "python -c \"from cryptography.fernet import Fernet; "
            "print(Fernet.generate_key().decode())\""
        )
    keys = [Fernet(k.strip().encode()) for k in raw.split(",") if k.strip()]
    return MultiFernet(keys)


_fernet = _build()


def encrypt(plaintext: str) -> str:
    return _fernet.encrypt(plaintext.encode("utf-8")).decode("utf-8")


def decrypt(ciphertext: str) -> str:
    return _fernet.decrypt(ciphertext.encode("utf-8")).decode("utf-8")


def last4(plaintext: str) -> str:
    """Last 4 chars, for a masked display hint. Computed before we discard the
    plaintext; never derived from ciphertext."""
    return plaintext[-4:] if len(plaintext) >= 4 else plaintext


def decrypt_safe(value: str) -> str:
    """Decrypt a value that MAY already be ciphertext. Links created before this
    field was encrypted — and the seed rows inserted by plain SQL — hold the
    question as plaintext, which is not a valid Fernet token. On any decrypt
    failure we return the value unchanged and treat it as the plaintext it is.
    New writes are always encrypted; an edit re-encrypts the row in place."""
    try:
        return decrypt(value)
    except Exception:
        return value