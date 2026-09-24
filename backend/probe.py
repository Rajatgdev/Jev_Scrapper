"""One-off proof that Firecrawl really scrapes the page. Run: python probe.py"""
import asyncio, json, httpx
from app.core.config import settings
from app.core.targets import TARGETS

async def main():
    url = TARGETS[0]["url"]
    payload = {
        "url": url,
        "formats": ["markdown", {"type": "changeTracking", "modes": ["git-diff"]}],
        "onlyMainContent": True,
    }
    headers = {"Authorization": f"Bearer {settings.firecrawl_api_key}"}
    async with httpx.AsyncClient(timeout=60) as c:
        r = await c.post("https://api.firecrawl.dev/v2/scrape", json=payload, headers=headers)
        r.raise_for_status()
        data = r.json().get("data", {})

    ct = data.get("changeTracking", {}) or {}
    md = data.get("markdown", "") or ""
    meta = data.get("metadata", {}) or {}

    print("URL scraped:      ", url)
    print("HTTP status:      ", meta.get("statusCode"))
    print("Credits used:     ", meta.get("creditsUsed"))
    print("changeStatus:     ", ct.get("changeStatus"))
    print("previousScrapeAt: ", ct.get("previousScrapeAt"))
    print("markdown length:  ", len(md), "chars")
    print("--- first 400 chars of scraped page ---")
    print(md[:400])

asyncio.run(main())