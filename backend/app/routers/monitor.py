"""API the frontend calls: run the monitor, and CRUD the watched links.

Links now live in Neon (see app/db/store.py), scoped to the seed user until
auth (step B) supplies a real user. The run reads links from the DB, runs the
pipeline, records the run, and returns the digest.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.db import store
from app.services import pipeline

router = APIRouter(prefix="/api", tags=["monitor"])


class TargetIn(BaseModel):
    title: str
    url: str
    question: str


@router.get("/targets")
async def list_targets():
    return await store.list_links()


@router.post("/targets")
async def add_target(t: TargetIn):
    try:
        return await store.add_link(t.title, t.url, t.question)
    except ValueError as e:
        raise HTTPException(409, str(e))


@router.put("/targets/{link_id}")
async def update_target(link_id: int, t: TargetIn):
    updated = await store.update_link(link_id, t.title, t.url, t.question)
    if updated is None:
        raise HTTPException(404, "Target not found")
    return updated


@router.delete("/targets/{link_id}")
async def delete_target(link_id: int):
    if not await store.delete_link(link_id):
        raise HTTPException(404, "Target not found")
    return {"deleted": link_id}


@router.post("/run")
async def run():
    """Run the monitor over the user's links, record the run, return the digest."""
    links = await store.list_links()
    targets = [{"title": l["title"], "url": l["url"], "question": l["question"]}
               for l in links if l["is_active"]]
    result = await pipeline.run_daily(targets)
    await store.record_run(result["digest"], result["survivor_count"], "manual")
    return result