"""Password hashing (Argon2id) and opaque session tokens.

Argon2id is the OWASP-recommended password hash. Hashing is CPU/memory heavy,
so it runs in a worker thread to avoid blocking the async event loop. Session
tokens are random; we store only their SHA-256 digest, never the raw token.
"""
import hashlib
import secrets

from anyio import to_thread
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, InvalidHashError

_ph = PasswordHasher()  # Argon2id defaults


async def hash_password(password: str) -> str:
    return await to_thread.run_sync(_ph.hash, password)


async def verify_password(encoded: str, password: str) -> bool:
    try:
        return bool(await to_thread.run_sync(_ph.verify, encoded, password))
    except (VerifyMismatchError, InvalidHashError):
        return False


# One precomputed hash to verify against for unknown accounts, so login timing
# doesn't reveal whether an email exists (mitigates account enumeration).
DUMMY_HASH = _ph.hash("timing-attack-dummy-password")


def new_session_token() -> str:
    """A fresh random bearer token for the cookie (raw value, shown once)."""
    return secrets.token_urlsafe(32)


def digest_token(token: str) -> str:
    """SHA-256 digest stored in the DB; the raw token never is."""
    return hashlib.sha256(token.encode()).hexdigest()