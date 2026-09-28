"""The monitoring flow, wired end to end. Plain orchestration — the intelligence
is in Jev (per chunk) and OpenAI (once per run).

run_for_url    : one page -> survivors (the core loop)
run_for_user   : all of ONE user's links -> digest, emailed to THAT user
run_daily      : the manual /api/run path for a given target list
"""
import asyncio
from app.core.config import settings
from app.models.schemas import ScoredChunk
from app.services import scraper, differ, jev, summariser, emailer


async def run_for_url(url: str, title: str, question: str) -> list[ScoredChunk]:
    """Scrape -> diff -> chunk -> Jev per chunk -> threshold. Returns survivors."""
    status, diff = await scraper.scrape_with_diff(url)
    if status != "changed" or not diff:
        return []  # unchanged pages exit here, before any Jev call

    chunks = differ.chunks_from_diff(diff, title, url, question)
    print(f"    [pipeline] {url}: {len(chunks)} chunk(s) from diff")

    # THE CORE LOOP: one Jev decision per changed paragraph.
    verdicts = await asyncio.gather(*(jev.evaluate(c) for c in chunks))

    scored = [ScoredChunk(chunk=c, verdict=v) for c, v in zip(chunks, verdicts)]

    for s in scored:
        v = s.verdict
        print(f"    [pipeline]   verdict: severity={v.severity} "
              f"sev_conf={v.severity_conf:.2f} relevant={v.relevant:.2f} "
              f"is_noise={v.is_noise:.2f} -> "
              f"{'KEEP' if v.passes(settings.severity_conf_min, settings.relevant_prob_min, settings.noise_prob_max) else 'drop'}")

    # Gate in plain code, using thresholds from config.
    return [
        s for s in scored
        if s.verdict.passes(
            settings.severity_conf_min,
            settings.relevant_prob_min,
            settings.noise_prob_max,
        )
    ]


async def _run_targets(targets: list[dict]) -> tuple[str, list[ScoredChunk]]:
    """Run a list of targets, summarise once. Returns (digest, survivors)."""
    all_survivors: list[ScoredChunk] = []
    for t in targets:
        all_survivors.extend(
            await run_for_url(t["url"], t["title"], t["question"]))
    digest = await summariser.summarise(all_survivors)  # skips call if empty
    return digest, all_survivors


async def run_for_user(targets: list[dict], email: str) -> dict:
    """Run ONE user's targets and email the digest to THAT user.

    Used by the scheduler. Emails only when there's something to report, so a
    quiet run doesn't spend on email or nag the user.
    """
    digest, survivors = await _run_targets(targets)
    if settings.send_email and survivors:
        await emailer.send_digest(digest, len(survivors), to=email)
    return {
        "digest": digest,
        "survivor_count": len(survivors),
        "survivors": [s.model_dump() for s in survivors],
    }


async def run_daily(targets: list[dict]) -> dict:
    """Manual /api/run path: run targets, email the configured recipient."""
    digest, survivors = await _run_targets(targets)
    if settings.send_email:
        await emailer.send_digest(digest, len(survivors))
    return {
        "digest": digest,
        "survivor_count": len(survivors),
        "survivors": [s.model_dump() for s in survivors],
    }