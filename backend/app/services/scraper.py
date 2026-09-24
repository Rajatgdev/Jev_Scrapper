"""Firecrawl scrape + change tracking. Returns (changed?, diff_text).

Firecrawl's git-diff mode is 1 credit/page and does the diffing for us, so this
module is thin on purpose. If Firecrawl renders a legacy gov portal badly, swap
this file for a ClawEngine/Apify implementation — nothing downstream changes.
"""
import httpx
from app.core.config import settings

FIRECRAWL_URL = "https://api.firecrawl.dev/v2/scrape"


async def scrape_with_diff(url: str) -> tuple[str, str | None]:
    """Returns (change_status, diff_text_or_None).

    change_status is "new" | "unchanged" | "changed".
    diff_text is the git-diff string, present only when status == "changed".
    """
    payload = {
        "url": url,
        "formats": ["markdown", {"type": "changeTracking", "modes": ["git-diff"]}],
        "onlyMainContent": True,  # keep diffs about content, not nav/footer churn
    }
    headers = {"Authorization": f"Bearer {settings.firecrawl_api_key}"}

    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.post(FIRECRAWL_URL, json=payload, headers=headers)
        r.raise_for_status()
        data = r.json().get("data", {})

    ct = data.get("changeTracking", {}) or {}
    status = ct.get("changeStatus", "new")
    diff = (ct.get("diff") or {}).get("text") if status == "changed" else None
    return status, diff
