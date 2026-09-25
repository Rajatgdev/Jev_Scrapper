"""API the frontend calls: run the monitor, and CRUD the watched targets.

Targets are seeded from targets.py and held in memory for the session. Adds/
edits/deletes from the UI last until restart/redeploy — full persistence
arrives when targets move to the database. The relevance question is per-target.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.core.targets import TARGETS
from app.services import pipeline
from app.db import store

router = APIRouter(prefix="/api", tags=["monitor"])

# In-memory working copy, seeded from the config file.
_targets: list[dict] = [dict(t) for t in TARGETS]


class TargetIn(BaseModel):
    title: str
    url: str
    question: str


@router.get("/targets")
def list_targets():
    return _targets


@router.post("/targets")
def add_target(t: TargetIn):
    if any(x["url"] == t.url for x in _targets):
        raise HTTPException(409, "A target with this URL already exists")
    _targets.append(t.model_dump())
    return t.model_dump()


@router.put("/targets/{index}")
def update_target(index: int, t: TargetIn):
    if not 0 <= index < len(_targets):
        raise HTTPException(404, "Target not found")
    _targets[index] = t.model_dump()
    return t.model_dump()


@router.delete("/targets/{index}")
def delete_target(index: int):
    if not 0 <= index < len(_targets):
        raise HTTPException(404, "Target not found")
    return _targets.pop(index)


@router.post("/run")
async def run():
    """Run the monitor over all current targets, return digest + survivors."""
    result = await pipeline.run_daily(_targets)
    store.save_run(result)  # no-op unless USE_DB=true
    return result