"""Database access for links and runs, against Neon Postgres.

Raw SQL over the async session (no ORM models — the schema lives in the .sql
migrations, this file just queries it). Step A is still effectively single-user:
everything is scoped to SEED_USER_ID until auth (step B) supplies a real user.
"""
from sqlalchemy import text

from app.db.session import SessionLocal

# Step A: one seed user owns everything. Step B replaces this with the
# authenticated user's id on each request.
SEED_USER_ID = 1

MAX_LINKS_PER_USER = 10


async def list_links(user_id: int = SEED_USER_ID) -> list[dict]:
    async with SessionLocal() as s:
        rows = await s.execute(
            text("SELECT id, title, url, question, is_active "
                 "FROM links WHERE user_id = :u ORDER BY id"),
            {"u": user_id},
        )
        return [dict(r._mapping) for r in rows]


async def add_link(title: str, url: str, question: str,
                   user_id: int = SEED_USER_ID) -> dict:
    async with SessionLocal() as s:
        count = await s.scalar(
            text("SELECT count(*) FROM links WHERE user_id = :u"), {"u": user_id})
        if count >= MAX_LINKS_PER_USER:
            raise ValueError(f"Link limit reached ({MAX_LINKS_PER_USER}).")
        exists = await s.scalar(
            text("SELECT 1 FROM links WHERE user_id = :u AND url = :url"),
            {"u": user_id, "url": url})
        if exists:
            raise ValueError("A target with this URL already exists.")
        row = await s.execute(
            text("INSERT INTO links (user_id, title, url, question) "
                 "VALUES (:u, :t, :url, :q) "
                 "RETURNING id, title, url, question, is_active"),
            {"u": user_id, "t": title, "url": url, "q": question})
        await s.commit()
        return dict(row.one()._mapping)


async def update_link(link_id: int, title: str, url: str, question: str,
                      user_id: int = SEED_USER_ID) -> dict | None:
    async with SessionLocal() as s:
        row = await s.execute(
            text("UPDATE links SET title = :t, url = :url, question = :q, "
                 "updated_at = now() "
                 "WHERE id = :id AND user_id = :u "
                 "RETURNING id, title, url, question, is_active"),
            {"id": link_id, "u": user_id, "t": title, "url": url, "q": question})
        await s.commit()
        r = row.first()
        return dict(r._mapping) if r else None


async def delete_link(link_id: int, user_id: int = SEED_USER_ID) -> bool:
    async with SessionLocal() as s:
        row = await s.execute(
            text("DELETE FROM links WHERE id = :id AND user_id = :u RETURNING id"),
            {"id": link_id, "u": user_id})
        await s.commit()
        return row.first() is not None


async def record_run(changes: list[dict], trigger: str = "manual",
                     user_id: int = SEED_USER_ID) -> None:
    """Persist a completed run. `changes` is the grouped change list; we store
    it as JSON in the digest column so the Digest page can render it."""
    import json
    async with SessionLocal() as s:
        await s.execute(
            text("INSERT INTO runs (user_id, finished_at, survivor_count, "
                 "digest, status, trigger) "
                 "VALUES (:u, now(), :c, :d, 'ok', :trg)"),
            {"u": user_id, "c": len(changes), "d": json.dumps(changes),
             "trg": trigger})
        await s.commit()


async def get_latest_run(user_id: int = SEED_USER_ID) -> dict | None:
    """The user's most recent run: its changes (parsed) and when it finished."""
    import json
    async with SessionLocal() as s:
        row = await s.execute(
            text("SELECT digest, finished_at, survivor_count FROM runs "
                 "WHERE user_id = :u AND status = 'ok' "
                 "ORDER BY finished_at DESC LIMIT 1"),
            {"u": user_id})
        r = row.first()
        if r is None:
            return None
        m = r._mapping
        try:
            changes = json.loads(m["digest"]) if m["digest"] else []
        except (json.JSONDecodeError, TypeError):
            changes = []
        return {
            "changes": changes,
            "finished_at": m["finished_at"].isoformat() if m["finished_at"] else None,
            "total": m["survivor_count"],
        }


async def all_active_users_with_links() -> list[dict]:
    """Every active user and their active links. For the scheduler.

    Returns [{id, email, links: [{title, url, question}, ...]}, ...],
    skipping users who have no active links (nothing to run).
    """
    async with SessionLocal() as s:
        rows = await s.execute(
            text("SELECT u.id, u.email, l.title, l.url, l.question "
                 "FROM users u JOIN links l ON l.user_id = u.id "
                 "WHERE u.is_active AND l.is_active "
                 "ORDER BY u.id"))
        users: dict[int, dict] = {}
        for r in rows:
            m = r._mapping
            u = users.setdefault(m["id"], {"id": m["id"], "email": m["email"],
                                           "links": []})
            u["links"].append({"title": m["title"], "url": m["url"],
                               "question": m["question"]})
        return list(users.values())