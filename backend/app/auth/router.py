"""Auth endpoints: signup, login, logout, me — and the current_user dependency.

Same-origin deployment (frontend proxies /api to this backend through Vercel),
so the session cookie is SameSite=Lax, Secure, HttpOnly. No CSRF token dance is
needed because the cookie isn't sent on cross-site requests.
"""
from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, HTTPException, Response, status
from pydantic import BaseModel, EmailStr

from app.auth import store
from app.auth.security import (
    DUMMY_HASH, hash_password, new_session_token, verify_password,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])

COOKIE_NAME = "session"
COOKIE_MAX_AGE = 7 * 24 * 3600  # matches ABSOLUTE_TTL


class Credentials(BaseModel):
    email: EmailStr
    password: str


def _set_cookie(resp: Response, token: str) -> None:
    resp.set_cookie(
        COOKIE_NAME, token,
        max_age=COOKIE_MAX_AGE,
        httponly=True,
        secure=True,
        samesite="lax",
        path="/",
    )


# ---- dependency ----

async def current_user(
    session: Annotated[str | None, Cookie(alias=COOKIE_NAME)] = None,
) -> dict:
    if not session:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not signed in")
    user = await store.user_for_token(session)
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Session expired")
    return user


CurrentUser = Annotated[dict, Depends(current_user)]


# ---- endpoints ----

@router.post("/signup")
async def signup(creds: Credentials, response: Response):
    if len(creds.password) < 8:
        raise HTTPException(400, "Password must be at least 8 characters")
    existing = await store.get_user_by_email(creds.email)
    if existing:
        # generic message — don't confirm which emails are registered
        raise HTTPException(409, "Could not create account with those details")
    ph = await hash_password(creds.password)
    user = await store.create_user(creds.email, ph)
    token = new_session_token()
    await store.create_session(user["id"], token)
    _set_cookie(response, token)
    return {"id": user["id"], "email": user["email"]}


@router.post("/login")
async def login(creds: Credentials, response: Response):
    user = await store.get_user_by_email(creds.email)
    # always run one verification (dummy if no user) to level timing
    hashed = user["password_hash"] if user and user["password_hash"] else DUMMY_HASH
    ok = await verify_password(hashed, creds.password)
    if not user or not ok or not user["is_active"]:
        raise HTTPException(401, "Incorrect email or password")
    token = new_session_token()
    await store.create_session(user["id"], token)
    _set_cookie(response, token)
    return {"id": user["id"], "email": user["email"]}


@router.post("/logout")
async def logout(response: Response,
                 session: Annotated[str | None, Cookie(alias=COOKIE_NAME)] = None):
    if session:
        await store.revoke_session(session)
    response.delete_cookie(COOKIE_NAME, path="/")
    return {"ok": True}


@router.get("/me")
async def me(user: CurrentUser):
    return user