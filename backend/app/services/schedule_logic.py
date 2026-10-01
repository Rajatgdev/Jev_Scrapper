"""When is a user's scheduled run due? Pure functions, no database.

A user picks a local hour (run_hour) and a timezone. The cron ticks hourly and
asks is_due(): has their run time passed today (in THEIR timezone) with no
scheduled run since then? This "catch-up" rule means a late or skipped tick
still runs them on the next tick, and a user is never run twice for one slot.
"""
from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

UTC = timezone.utc


def valid_timezone(name: str) -> bool:
    try:
        ZoneInfo(name)
        return True
    except Exception:
        return False


def last_boundary_utc(run_hour: int, tz_name: str, now_utc: datetime) -> datetime:
    """The most recent moment (in UTC) at which this user's run time occurred."""
    tz = ZoneInfo(tz_name)
    now_local = now_utc.astimezone(tz)
    day = now_local.date()
    if now_local.hour < run_hour:
        day = day - timedelta(days=1)
    boundary_local = datetime.combine(day, time(run_hour), tzinfo=tz)
    return boundary_local.astimezone(UTC)


def is_due(run_hour: int, tz_name: str, last_attempt_utc, now_utc: datetime) -> bool:
    """True if the user's run time has passed and no scheduled run happened since."""
    boundary = last_boundary_utc(run_hour, tz_name, now_utc)
    if last_attempt_utc is None:
        return True
    if last_attempt_utc.tzinfo is None:
        last_attempt_utc = last_attempt_utc.replace(tzinfo=UTC)
    return last_attempt_utc < boundary