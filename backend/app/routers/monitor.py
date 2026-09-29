"""API the frontend calls: run the monitor, and CRUD the watched links.

Every endpoint requires a signed-in user and is scoped to that user's data.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.auth.router import CurrentUser
from app.db import store
from app.services import pipeline

router = APIRouter(prefix="/api", tags=["monitor"])


class TargetIn(BaseModel):
    title: str
    url: str
    question: str


@router.get("/targets")
async def list_targets(user: CurrentUser):
    return await store.list_links(user["id"])


@router.post("/targets")
async def add_target(t: TargetIn, user: CurrentUser):
    try:
        return await store.add_link(t.title, t.url, t.question, user["id"])
    except ValueError as e:
        raise HTTPException(409, str(e))


@router.put("/targets/{link_id}")
async def update_target(link_id: int, t: TargetIn, user: CurrentUser):
    updated = await store.update_link(link_id, t.title, t.url, t.question, user["id"])
    if updated is None:
        raise HTTPException(404, "Target not found")
    return updated


@router.delete("/targets/{link_id}")
async def delete_target(link_id: int, user: CurrentUser):
    if not await store.delete_link(link_id, user["id"]):
        raise HTTPException(404, "Target not found")
    return {"deleted": link_id}


@router.post("/run")
async def run(user: CurrentUser):
    """Run the monitor over the user's links, record the run, return changes."""
    links = await store.list_links(user["id"])
    targets = [{"title": l["title"], "url": l["url"], "question": l["question"]}
               for l in links if l["is_active"]]
    result = await pipeline.run_daily(targets)
    await store.record_run(result["briefing"], result["changes"], "manual", user["id"])
    return result


@router.get("/digest")
async def digest(user: CurrentUser):
    """The user's latest run: briefing + changes, for the Digest home page."""
    source_count = len([l for l in await store.list_links(user["id"]) if l["is_active"]])
    latest = await store.get_latest_run(user["id"])
    if latest is None:
        return {"briefing": "", "changes": [],
                "counts": {"high": 0, "medium": 0, "low": 0},
                "total": 0, "finished_at": None, "source_count": source_count}
    changes = latest["changes"]
    counts = {k: sum(c.get("severity") == k for c in changes)
              for k in ("high", "medium", "low")}
    return {"briefing": latest.get("briefing", ""), "changes": changes,
            "counts": counts, "total": latest["total"],
            "finished_at": latest["finished_at"], "source_count": source_count}