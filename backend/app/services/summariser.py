"""The single OpenAI call per run. Runs only over chunks Jev already blessed as
high-severity AND on-topic. If the survivor list is empty, it is NOT called.

Prose is the one thing Jev cannot do. Cost scales with real regulatory events,
not with page churn.
"""
import httpx
from app.core.config import settings
from app.models.schemas import ScoredChunk

OPENAI_URL = "https://api.openai.com/v1/chat/completions"

SYSTEM = (
    "You write concise regulatory-change briefings. You are given "
    "pre-classified high-importance changes. Group by page, lead with the most "
    "consequential, state plainly what changed from old to new. No speculation, "
    "no filler."
)


async def summarise(survivors: list[ScoredChunk]) -> str:
    if not survivors:
        return "No significant changes today."

    rows = [
        {
            "page": s.chunk.page_title,
            "url": s.chunk.page_url,
            "old": s.chunk.old_text,
            "new": s.chunk.new_text,
            "severity": s.verdict.severity,
            "confidence": round(s.verdict.severity_conf, 2),
        }
        for s in survivors
    ]

    payload = {
        "model": settings.openai_model,
        "messages": [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": str(rows)},
        ],
    }
    headers = {"Authorization": f"Bearer {settings.openai_api_key}"}

    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.post(OPENAI_URL, json=payload, headers=headers)
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]
