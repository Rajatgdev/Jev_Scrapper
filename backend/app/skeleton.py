"""THE WALKING SKELETON. Run this first:  python -m app.skeleton

It proves the whole idea on ONE change, end to end, and burns ~1 Firecrawl credit.

Two modes:
  - Keys set in .env  -> hits Firecrawl + Jev for real on the first target.
  - No keys / --mock  -> uses a hard-coded diff so you can see the pipeline shape
                          (chunking -> Jev contract -> threshold) with zero network.

Start in --mock to see the flow, then set keys and run for real.
"""
import argparse
import asyncio
from app.core.config import settings
from app.core.targets import TARGETS
from app.models.schemas import Chunk, Verdict, ScoredChunk
from app.services import differ, jev, pipeline

# A realistic git-diff: a duty rate moved 0% -> 5% (high), plus a footer date
# tweak (noise). Lets you watch the gate keep one and drop the other.
MOCK_DIFF = """@@ -1,4 +1,4 @@
 Import controls for chemical products
-Duty rate on listed substances: 0%
+Duty rate on listed substances: 5%
 Applies to Annex II chemicals.
@@ -12,2 +12,2 @@
-Last updated: 3 January 2026
+Last updated: 4 January 2026
"""


async def real_run():
    all_survivors = []
    for t in TARGETS:
        print(f"[real] scraping {t['url']}")
        survivors = await pipeline.run_for_url(t["url"], t["title"])
        all_survivors.extend(survivors)
    _report(all_survivors)


async def mock_run():
    print("[mock] no network — using a canned diff\n")
    chunks = differ.chunks_from_diff(MOCK_DIFF, "Import controls: chemicals",
                                     "https://example.gov/customs/chemicals")
    print(f"chunked into {len(chunks)} change(s):")
    for c in chunks:
        print(f"  - OLD: {c.old_text!r}\n    NEW: {c.new_text!r}")

    # Mock Jev verdicts so the skeleton runs with zero keys. The REAL jev.evaluate
    # sends these same three typed questions to Jev.
    mock_verdicts = [
        Verdict(severity="high", severity_conf=0.91, relevant=0.88,
                is_noise=0.05),
        Verdict(severity="low", severity_conf=0.80, relevant=0.72,
                is_noise=0.94),
    ]
    scored = [ScoredChunk(chunk=c, verdict=v)
              for c, v in zip(chunks, mock_verdicts)]
    survivors = [s for s in scored if s.verdict.passes(
        settings.severity_conf_min, settings.relevant_prob_min,
        settings.noise_prob_max)]
    _report(survivors)


async def jev_test_run():
    """Send ONE hard-coded chunk to the REAL Jev API and print the raw verdict.
    Proves the live Jev integration — auth, request shape, response parsing —
    without scraping or waiting for a real page change."""
    chunk = Chunk(
        page_title="Import controls: chemicals",
        page_url="https://example.gov/customs/chemicals",
        old_text="Duty rate on listed substances: 0%",
        new_text="Duty rate on listed substances: 5%",
    )
    print("[jev-test] sending one chunk to the real Jev API...")
    print(f"  OLD: {chunk.old_text!r}")
    print(f"  NEW: {chunk.new_text!r}\n")
    v = await jev.evaluate(chunk)
    print(f"{'='*54}\nRaw Jev verdict:")
    print(f"  severity   : {v.severity}  (confidence {v.severity_conf:.2f})")
    print(f"  relevant   : {v.relevant:.2f}   (Noul: P(on-topic))")
    print(f"  is_noise   : {v.is_noise:.2f}   (Noul: P(cosmetic))")
    passed = v.passes(settings.severity_conf_min, settings.relevant_prob_min,
                      settings.noise_prob_max)
    print(f"  -> passes the gate: {passed}")
    print("=" * 54)


def _report(survivors: list[ScoredChunk]):
    print(f"\n{'='*54}\nJev kept {len(survivors)} survivor(s) after the gate:")
    for s in survivors:
        v = s.verdict
        print(f"  [{v.severity} {v.severity_conf:.2f} | "
              f"relevant={v.relevant:.2f}]  {s.chunk.new_text!r}")
    if not survivors:
        print("  (nothing high + relevant — no email would be sent)")
    print("="*54)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--mock", action="store_true",
                    help="run with a canned diff and mock Jev, no network")
    ap.add_argument("--jev-test", action="store_true",
                    help="send one hard-coded chunk to the REAL Jev API only")
    args = ap.parse_args()

    if args.jev_test:
        if not settings.jev_api_key:
            raise SystemExit("--jev-test needs JEV_API_KEY set in .env")
        asyncio.run(jev_test_run())
    elif args.mock or not (settings.firecrawl_api_key and settings.jev_api_key):
        asyncio.run(mock_run())
    else:
        asyncio.run(real_run())
