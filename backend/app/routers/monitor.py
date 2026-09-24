"""API the frontend calls. One endpoint to trigger a run and get the digest."""
from fastapi import APIRouter
from app.core.targets import TARGETS
from app.services import pipeline
from app.db import store

router = APIRouter(prefix="/api", tags=["monitor"])


@router.post("/run")
async def run():
    """Run the monitor over all targets, return the digest + survivors."""
    result = await pipeline.run_daily(TARGETS)
    store.save_run(result)  # no-op unless USE_DB=true
    return result


@router.get("/targets")
def targets():
    """List the pages being watched (for the dashboard)."""
    return TARGETS
