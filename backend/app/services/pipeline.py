"""The daily flow, wired end to end. Plain orchestration — the intelligence is
in Jev (per chunk) and OpenAI (once)."""
import asyncio
from app.core.config import settings
from app.models.schemas import ScoredChunk
from app.services import scraper, differ, jev, summariser


async def run_for_url(url: str, title: str) -> list[ScoredChunk]:
    """Scrape -> diff -> chunk -> Jev per chunk -> threshold. Returns survivors."""
    status, diff = await scraper.scrape_with_diff(url)
    if status != "changed" or not diff:
        return []  # unchanged pages exit here, before any Jev call

    chunks = differ.chunks_from_diff(diff, title, url)

    # THE CORE LOOP: one Jev decision per changed paragraph.
    verdicts = await asyncio.gather(*(jev.evaluate(c) for c in chunks))

    scored = [ScoredChunk(chunk=c, verdict=v) for c, v in zip(chunks, verdicts)]

    # Gate in plain code, using thresholds from config.
    return [
        s for s in scored
        if s.verdict.passes(
            settings.severity_conf_min,
            settings.relevant_prob_min,
            settings.noise_prob_max,
        )
    ]


async def run_daily(targets: list[dict]) -> dict:
    """Run every target, summarise survivors once, return the digest + detail."""
    all_survivors: list[ScoredChunk] = []
    for t in targets:
        all_survivors.extend(await run_for_url(t["url"], t["title"]))

    digest = await summariser.summarise(all_survivors)  # skips call if empty
    return {
        "digest": digest,
        "survivor_count": len(all_survivors),
        "survivors": [s.model_dump() for s in all_survivors],
    }
