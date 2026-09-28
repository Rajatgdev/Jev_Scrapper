"""The monitoring flow. Jev SORTS every real change by severity; nothing is
dropped for being low. Only pure noise and off-topic changes are filtered.

run_for_url  : one page -> kept ScoredChunks (any severity)
run_for_user : all of ONE user's links -> grouped changes, emailed to that user
run_daily    : the manual /api/run path
"""
import asyncio
from app.core.config import settings
from app.models.schemas import Change, ScoredChunk
from app.services import scraper, differ, jev, summariser, emailer

SEV_ORDER = {"high": 0, "medium": 1, "low": 2}


async def run_for_url(url: str, title: str, question: str) -> list[ScoredChunk]:
    """Scrape -> diff -> chunk -> Jev per chunk -> keep real on-topic changes."""
    status, diff = await scraper.scrape_with_diff(url)
    if status != "changed" or not diff:
        return []

    chunks = differ.chunks_from_diff(diff, title, url, question)
    print(f"    [pipeline] {url}: {len(chunks)} chunk(s) from diff")

    verdicts = await asyncio.gather(*(jev.evaluate(c) for c in chunks))
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


async def _collect(targets: list[dict]) -> list[Change]:
    """Run all targets, keep+summarise changes, return them sorted by severity."""
    survivors: list[ScoredChunk] = []
    for t in targets:
        survivors.extend(
            await run_for_url(t["url"], t["title"], t["question"]))
    changes = await summariser.summarise(survivors)   # [] if nothing kept
    changes.sort(key=lambda c: SEV_ORDER.get(c.severity, 3))
    return changes


def _counts(changes: list[Change]) -> dict:
    return {
        "high": sum(c.severity == "high" for c in changes),
        "medium": sum(c.severity == "medium" for c in changes),
        "low": sum(c.severity == "low" for c in changes),
    }


def _result(changes: list[Change]) -> dict:
    return {
        "changes": [c.model_dump() for c in changes],
        "counts": _counts(changes),
        "total": len(changes),
    }


async def run_for_user(targets: list[dict], email: str) -> dict:
    """Scheduler path: run a user's targets, email them if anything changed."""
    changes = await _collect(targets)
    if settings.send_email and changes:
        await emailer.send_digest(changes, email)
    return _result(changes)


async def run_daily(targets: list[dict]) -> dict:
    """Manual /api/run path."""
    changes = await _collect(targets)
    if settings.send_email and changes:
        await emailer.send_digest(changes, settings.digest_to)
    return _result(changes)