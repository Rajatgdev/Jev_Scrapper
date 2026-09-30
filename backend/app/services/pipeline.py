"""The monitoring flow. Jev SORTS every real change by severity; nothing is
dropped for being low. Only pure noise and off-topic changes are filtered.

Every run uses the RUNNING USER'S OWN keys (openai, firecrawl, jev), decrypted
per-run and passed down — never globals, never logged. A user missing any key
cannot run (MissingKeysError).
"""
import asyncio
from app.core.config import settings
from app.models.schemas import Change, ScoredChunk
from app.services import scraper, differ, jev, summariser, emailer

SEV_ORDER = {"high": 0, "medium": 1, "low": 2}
REQUIRED_PROVIDERS = ("openai", "firecrawl", "jev")


class MissingKeysError(Exception):
    """Raised when the running user hasn't configured all required API keys."""
    def __init__(self, missing: list[str]):
        self.missing = missing
        super().__init__(f"Missing API keys: {', '.join(missing)}")


async def run_for_url(url: str, title: str, question: str, keys: dict) -> list[ScoredChunk]:
    """Scrape -> diff -> chunk -> Jev per chunk -> keep real on-topic changes.
    `keys` is {openai, firecrawl, jev} — the user's own decrypted keys."""
    status, diff = await scraper.scrape_with_diff(url, keys["firecrawl"])
    if status != "changed" or not diff:
        return []

    chunks = differ.chunks_from_diff(diff, title, url, question)
    print(f"    [pipeline] {url}: {len(chunks)} chunk(s) from diff")

    verdicts = await asyncio.gather(*(jev.evaluate(c, keys["jev"]) for c in chunks))
    scored = [ScoredChunk(chunk=c, verdict=v) for c, v in zip(chunks, verdicts)]

    kept = []
    for s in scored:
        v = s.verdict
        ok = v.keep(settings.relevant_prob_min, settings.noise_prob_max)
        print(f"    [pipeline]   severity={v.severity} relevant={v.relevant:.2f} "
              f"is_noise={v.is_noise:.2f} -> {'KEEP' if ok else 'drop'}")
        if ok:
            kept.append(s)
    return kept


def _require_keys(keys: dict) -> None:
    missing = [p for p in REQUIRED_PROVIDERS if not keys.get(p)]
    if missing:
        raise MissingKeysError(missing)


async def _collect(targets: list[dict], keys: dict) -> tuple[str, list[Change]]:
    """Run all targets, keep+summarise changes. Returns (briefing, sorted changes)."""
    survivors: list[ScoredChunk] = []
    for t in targets:
        survivors.extend(
            await run_for_url(t["url"], t["title"], t["question"], keys))
    briefing, changes = await summariser.summarise(survivors, keys["openai"])
    changes.sort(key=lambda c: SEV_ORDER.get(c.severity, 3))
    return briefing, changes


def _counts(changes: list[Change]) -> dict:
    return {
        "high": sum(c.severity == "high" for c in changes),
        "medium": sum(c.severity == "medium" for c in changes),
        "low": sum(c.severity == "low" for c in changes),
    }


def _result(briefing: str, changes: list[Change]) -> dict:
    return {
        "briefing": briefing,
        "changes": [c.model_dump() for c in changes],
        "counts": _counts(changes),
        "total": len(changes),
    }


async def run_for_user(targets: list[dict], email: str, keys: dict) -> dict:
    """Scheduler path: run a user's targets with their keys, email if changed."""
    _require_keys(keys)
    briefing, changes = await _collect(targets, keys)
    if settings.send_email and changes:
        await emailer.send_digest(briefing, changes, email)
    return _result(briefing, changes)


async def run_daily(targets: list[dict], keys: dict,
                    email: str | None = None) -> dict:
    """Manual /api/run path: run with the user's keys, email them if changed."""
    _require_keys(keys)
    briefing, changes = await _collect(targets, keys)
    recipient = email or settings.digest_to
    if settings.send_email and changes:
        await emailer.send_digest(briefing, changes, recipient)
    return _result(briefing, changes)