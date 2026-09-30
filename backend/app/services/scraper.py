"""Firecrawl scrape + change tracking. Returns (change_status, diff_text).

Firecrawl's git-diff mode is 1 credit/page and does the diffing for us. Change
tracking compares the scraped MARKDOWN against the previous scrape of the same
(url + team + markdown + tag). For reliable detection across runs we:
  - send a stable `tag` so every run shares one baseline (app + cron alike),
  - keep content-shaping options identical between runs,
  - log what Firecrawl actually returned, so a "0 flagged" is explainable.
"""
import httpx
from app.core.config import settings

FIRECRAWL_URL = "https://api.firecrawl.dev/v2/scrape"

# Stable tag so the manual app path and the cron share ONE comparison baseline.
CHANGE_TAG = "sentinel-v1"


async def scrape_with_diff(url: str, firecrawl_key: str) -> tuple[str, str | None]:
    """Returns (change_status, diff_text_or_None).

    change_status is "new" | "same" | "changed" | "removed".
    diff_text is the git-diff string, present only when status == "changed".
    """
    payload = {
        "url": url,
        "formats": [
            "markdown",
            {"type": "changeTracking", "modes": ["git-diff"], "tag": CHANGE_TAG},
        ],
        # NOTE: onlyMainContent must stay constant across runs or comparisons
        # break. We set it False so list/news content isn't stripped from the
        # markdown that change-tracking compares.
        "onlyMainContent": False,
    }
    headers = {"Authorization": f"Bearer {firecrawl_key}"}

    async with httpx.AsyncClient(timeout=90) as client:
        r = await client.post(FIRECRAWL_URL, json=payload, headers=headers)
        r.raise_for_status()
        body = r.json()

    data = body.get("data", {}) or {}
    ct = data.get("changeTracking", {}) or {}
    status = ct.get("changeStatus", "new")
    prev = ct.get("previousScrapeAt")
    md_len = len(data.get("markdown") or "")
    warning = body.get("warning") or data.get("warning")

    # Diagnostic line — shows up in the cron logs so 0-flagged is explainable.
    print(f"    [scraper] {url} -> status={status} "
          f"previousScrapeAt={prev} markdown_chars={md_len}"
          + (f" WARNING={warning}" if warning else ""))

    diff = (ct.get("diff") or {}).get("text") if status == "changed" else None
    if status == "changed":
        print(f"    [scraper]   diff present={diff is not None} "
              f"diff_chars={len(diff) if diff else 0}")
    return status, diff