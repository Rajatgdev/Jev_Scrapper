"""State store. OFF by default.

v1 needs almost no DB: Firecrawl retains page snapshots server-side and reports
new/unchanged/changed itself, so you can run the whole monitor with no database.
This module gives you a place to persist Jev verdicts and sent-digest logs when
you want an audit trail.

- USE_DB=false (default): every function is a no-op. The monitor still works.
- USE_DB=true + DATABASE_URL set: wire Neon Postgres here (SQLAlchemy already in
  requirements). Nothing upstream changes — the pipeline just calls save_run().
"""
from app.core.config import settings


def enabled() -> bool:
    return settings.use_db and bool(settings.database_url)


def save_run(result: dict) -> None:
    """Persist a daily run (digest + verdicts). No-op until USE_DB=true."""
    if not enabled():
        return
    # TODO(neon): open a SQLAlchemy session against settings.database_url and
    # insert the run. Left unimplemented on purpose — DB is opt-in.
    raise NotImplementedError("Neon DB layer not wired yet — set up when USE_DB=true")
