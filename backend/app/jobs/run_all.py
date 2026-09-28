"""Railway Cron entry (second service, same repo). Runs every user's monitor.

OPTION A (current): runs ALL active users every time the cron fires. Per-user
run_hour/timezone is ignored — see docs/multi-user-design.md for Option B, the
per-user-timing version to switch to at a daily cadence.

Must run to completion and exit cleanly (dispose the engine), or Railway skips
the next scheduled run. No HTTP, no auth cookie needed — it calls the pipeline
directly.

    python -m app.jobs.run_all
"""
import asyncio

from app.db import store
from app.db.session import engine
from app.services import pipeline


async def _main() -> None:
    users = await store.all_active_users_with_links()
    print(f"run_all: {len(users)} user(s) with active links")

    total_changes = 0
    for u in users:
        try:
            result = await pipeline.run_for_user(u["links"], u["email"])
            total_changes += result["total"]
            await store.record_run(result["changes"], "scheduled", u["id"])
            c = result["counts"]
            print(f"  user {u['id']} ({u['email']}): "
                  f"{len(u['links'])} link(s), {result['total']} change(s) "
                  f"({c['high']} high, {c['medium']} med, {c['low']} low)")
        except Exception as e:
            # one user's failure must not stop the rest
            print(f"  user {u['id']} ({u['email']}): ERROR {e!r}")

    await engine.dispose()  # release DB connections so the cron exits clean
    print(f"run_all: done, {total_changes} total change(s)")


def main() -> None:
    asyncio.run(_main())


if __name__ == "__main__":
    main()