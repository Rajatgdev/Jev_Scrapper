"""Settings API: manage each user's own OpenAI + Firecrawl keys.

Reads return only status (configured / last4), never the key. Writes validate
the key with a live provider call before encrypting and storing it.
"""
import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.auth.router import CurrentUser
from app.core import crypto
from app.db import store

router = APIRouter(prefix="/api/keys", tags=["keys"])

PROVIDERS = ("openai", "firecrawl")


class KeyIn(BaseModel):
    key: str


async def _validate(provider: str, key: str) -> None:
    """Live test the key. Raises HTTPException if it doesn't authenticate."""
    try:
        async with httpx.AsyncClient(timeout=15) as c:
            if provider == "openai":
                r = await c.get("https://api.openai.com/v1/models",
                                headers={"Authorization": f"Bearer {key}"})
            else:  # firecrawl
                r = await c.get("https://api.firecrawl.dev/v2/team/credit-usage",
                                headers={"Authorization": f"Bearer {key}"})
    except httpx.RequestError:
        raise HTTPException(503, "Could not reach the provider to validate the key. Try again.")
    if r.status_code in (401, 403):
        raise HTTPException(400, "That key was rejected by the provider. Check it and try again.")
    if r.status_code >= 400:
        raise HTTPException(400, "The key could not be validated. Check it and try again.")


@router.get("")
async def list_keys(user: CurrentUser):
    stored = await store.get_user_keys(user["id"])
    return {p: stored.get(p, {"configured": False, "last4": "", "updated_at": None})
            for p in PROVIDERS}


@router.put("/{provider}")
async def set_key(provider: str, body: KeyIn, user: CurrentUser):
    if provider not in PROVIDERS:
        raise HTTPException(404, "Unknown provider")
    key = body.key.strip()
    if not key:
        raise HTTPException(400, "Key is empty")
    await _validate(provider, key)
    await store.set_user_key(
        user["id"], provider, crypto.encrypt(key), crypto.last4(key),
        crypto.CRYPTO_VERSION, "v1")
    return {"provider": provider, "configured": True, "last4": crypto.last4(key)}


@router.delete("/{provider}")
async def delete_key(provider: str, user: CurrentUser):
    if provider not in PROVIDERS:
        raise HTTPException(404, "Unknown provider")
    await store.delete_user_key(user["id"], provider)
    return {"provider": provider, "configured": False,
            "note": "Remember to also revoke this key in your provider account."}