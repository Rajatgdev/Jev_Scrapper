"""Railway Cron entry (second service, same repo). Runs each user's monitor at
THEIR chosen time.

Schedule this service HOURLY in Railway (cron: 0 * * * *, which is UTC). Each
tick looks at every user and runs only those who are due: their chosen local
run time (run_hour in their timezone) has passed and they have no scheduled run
since. See app/services/schedule_logic.py. Users who aren't due cost nothing:
no scrapes, no API calls.

Must run to completion and exit cleanly (dispose the engine).

    python -m app.jobs.run_all
"""
import asyncio
from datetime import datetime, timezone

from app.db import store
from app.db.session import engine
from app.services import pipeline
from app.services.schedule_logic import is_due


async def _main() -> None:
    now = datetime.now(timezone.utc)
    users = await store.all_active_users_with_links()
    print(f"run_all: {len(users)} user(s) with active links, now={now.isoformat()}")

    total_changes = 0
    ran = 0
    for u in users:
        try:
            sched = await store.get_schedule(u["id"])
            last = await store.last_scheduled_attempt(u["id"])
            if not is_due(sched["run_hour"], sched["timezone"], last, now):
                continue  # not this user's time yet (or already ran for this slot)

            keys = await store.get_decrypted_keys(u["id"])
            missing = [p for p in ("openai", "firecrawl", "jev") if not keys.get(p)]
            if missing:
                print(f"  user {u['id']} ({u['email']}): SKIPPED — missing keys "
                      f"({', '.join(missing)})")
                continue

            ran += 1
            try:
                result = await pipeline.run_for_user(u["links"], u["email"], keys)
            except Exception:
                # count the attempt so a persistent failure doesn't retry hourly
                await store.record_failed_run(u["id"])
                raise
            total_changes += result["total"]
            await store.record_run(result["briefing"], result["changes"], "scheduled", u["id"])
            c = result["counts"]
            print(f"  user {u['id']} ({u['email']}): "
                  f"{len(u['links'])} link(s), {result['total']} change(s) "
                  f"({c['high']} high, {c['medium']} med, {c['low']} low)")
        except Exception as e:
            # one user's failure must not stop the rest
            print(f"  user {u['id']} ({u['email']}): ERROR {e!r}")

    await engine.dispose()  # release DB connections so the cron exits clean
    print(f"run_all: done, {ran} user(s) run, {total_changes} total change(s)")


def main() -> None:
    asyncio.run(_main())


if __name__ == "__main__":
    main()