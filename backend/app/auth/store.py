"""User and session database access for auth. Raw SQL over the async session."""
from datetime import datetime, timedelta, timezone

from sqlalchemy import text

from app.auth.security import digest_token
from app.db.session import SessionLocal

IDLE_TTL = timedelta(hours=24)       # session dies after 24h of no use
ABSOLUTE_TTL = timedelta(days=7)     # hard ceiling regardless of use


def _now() -> datetime:
    return datetime.now(timezone.utc)


# ---- users ----

async def get_user_by_email(email: str) -> dict | None:
    async with SessionLocal() as s:
        row = await s.execute(
            text("SELECT id, email, password_hash, is_active "
                 "FROM users WHERE email = :e"),
            {"e": email.lower().strip()})
        r = row.first()
        return dict(r._mapping) if r else None


async def create_user(email: str, password_hash: str) -> dict:
    async with SessionLocal() as s:
        row = await s.execute(
            text("INSERT INTO users (email, password_hash) "
                 "VALUES (:e, :p) RETURNING id, email, is_active"),
            {"e": email.lower().strip(), "p": password_hash})
        await s.commit()
        return dict(row.one()._mapping)


# ---- sessions ----

async def create_session(user_id: int, token: str) -> None:
    now = _now()
    async with SessionLocal() as s:
        await s.execute(
            text("INSERT INTO sessions (user_id, token_digest, idle_expires_at, "
                 "absolute_expires_at) VALUES (:u, :d, :idle, :abs)"),
            {"u": user_id, "d": digest_token(token),
             "idle": now + IDLE_TTL, "abs": now + ABSOLUTE_TTL})
        await s.commit()


async def user_for_token(token: str) -> dict | None:
    """Return the active user for a session token, or None. Refreshes idle TTL."""
    now = _now()
    async with SessionLocal() as s:
        row = await s.execute(
            text("SELECT s.id AS sid, s.idle_expires_at, s.absolute_expires_at, "
                 "s.revoked_at, u.id, u.email, u.is_active "
                 "FROM sessions s JOIN users u ON u.id = s.user_id "
                 "WHERE s.token_digest = :d"),
            {"d": digest_token(token)})
        r = row.first()
        if r is None:
            return None
        m = r._mapping
        if (m["revoked_at"] is not None
                or m["idle_expires_at"] < now
                or m["absolute_expires_at"] < now
                or not m["is_active"]):
            return None
        # slide the idle window forward, capped at absolute expiry
        new_idle = min(now + IDLE_TTL, m["absolute_expires_at"])
        await s.execute(
            text("UPDATE sessions SET last_seen_at = :n, idle_expires_at = :i "
                 "WHERE id = :sid"),
            {"n": now, "i": new_idle, "sid": m["sid"]})
        await s.commit()
        return {"id": m["id"], "email": m["email"]}


async def revoke_session(token: str) -> None:
    async with SessionLocal() as s:
        await s.execute(
            text("UPDATE sessions SET revoked_at = now() "
                 "WHERE token_digest = :d AND revoked_at IS NULL"),
            {"d": digest_token(token)})
        await s.commit()