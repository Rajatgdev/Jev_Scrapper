"""One OpenAI call per run: write a clean one-line summary for EACH kept change.

Input: the kept ScoredChunks (any severity). Output: a list of Change objects,
one per chunk, each with a short human summary. Jev already labelled severity;
OpenAI only writes prose. Returns [] for no input (no call made).
"""
import json
import httpx
from app.core.config import settings
from app.models.schemas import Change, ScoredChunk

OPENAI_URL = "https://api.openai.com/v1/chat/completions"

SYSTEM = (
    "You summarise webpage changes for a monitoring digest. You are given a "
    "JSON array of changes, each with an index, the page, and the old and new "
    "text. For each, write ONE short, plain sentence saying what changed. No "
    "preamble, no speculation. Respond with ONLY a JSON array of objects "
    '{"index": <int>, "summary": "<one sentence>"}, same length and order as '
    "the input. Return nothing but the JSON array."
)


async def summarise(survivors: list[ScoredChunk]) -> list[Change]:
    if not survivors:
        return []

    rows = [
        {"index": i, "page": s.chunk.page_title,
         "old": s.chunk.old_text[:500], "new": s.chunk.new_text[:500]}
        for i, s in enumerate(survivors)
    ]
    payload = {
        "model": settings.openai_model,
        "messages": [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": json.dumps(rows)},
        ],
    }
    headers = {"Authorization": f"Bearer {settings.openai_api_key}"}

    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.post(OPENAI_URL, json=payload, headers=headers)
        r.raise_for_status()
        content = r.json()["choices"][0]["message"]["content"].strip()

    # tolerate a ```json fence if the model adds one
    if content.startswith("```"):
        content = content.strip("`").lstrip("json").strip()

    summaries: dict[int, str] = {}
    try:
        for item in json.loads(content):
            summaries[int(item["index"])] = item["summary"]
    except (json.JSONDecodeError, KeyError, TypeError, ValueError):
        # fall back to the raw new text if the model misbehaves
        summaries = {}

    changes: list[Change] = []
    for i, s in enumerate(survivors):
        summary = summaries.get(i) or (s.chunk.new_text[:160] or "(content changed)")
        changes.append(Change(
            page_title=s.chunk.page_title,
            page_url=s.chunk.page_url,
            severity=s.verdict.severity,
            summary=summary,
        ))
    return changes