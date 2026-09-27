"""One-off: set (or reset) a user's password. Run:

    python -m app.auth.set_password owner@sentinel.local 'your-password'

Use it to give the seed user a password so you can log in, or to reset any
account. Creates the user if the email doesn't exist.
"""
import asyncio
import sys

from app.auth import store
from app.auth.security import hash_password
from app.db.session import SessionLocal
from sqlalchemy import text


async def main(email: str, password: str) -> None:
    ph = await hash_password(password)
    async with SessionLocal() as s:
        existing = await s.execute(
            text("SELECT id FROM users WHERE email = :e"), {"e": email.lower()})
        if existing.first():
            await s.execute(
                text("UPDATE users SET password_hash = :p WHERE email = :e"),
                {"p": ph, "e": email.lower()})
            print(f"password updated for {email}")
        else:
            await s.execute(
                text("INSERT INTO users (email, password_hash) VALUES (:e, :p)"),
                {"e": email.lower(), "p": ph})
            print(f"user {email} created")
        await s.commit()


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit("usage: python -m app.auth.set_password EMAIL PASSWORD")
    asyncio.run(main(sys.argv[1], sys.argv[2]))