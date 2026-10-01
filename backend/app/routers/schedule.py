"""Settings API: when each user's scheduled digest runs."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.auth.router import CurrentUser
from app.db import store
from app.services.schedule_logic import valid_timezone

router = APIRouter(prefix="/api/schedule", tags=["schedule"])


class ScheduleIn(BaseModel):
    run_hour: int
    timezone: str


@router.get("")
async def get_schedule(user: CurrentUser):
    return await store.get_schedule(user["id"])


@router.put("")
async def put_schedule(body: ScheduleIn, user: CurrentUser):
    if not 0 <= body.run_hour <= 23:
        raise HTTPException(400, "Hour must be between 0 and 23.")
    if not valid_timezone(body.timezone):
        raise HTTPException(400, "Unknown timezone.")
    await store.set_schedule(user["id"], body.run_hour, body.timezone)
    return {"run_hour": body.run_hour, "timezone": body.timezone}