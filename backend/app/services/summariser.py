"""One OpenAI call per run. Produces two levels of content for the digest:

  - a run-level `briefing`: a short paragraph overview of everything that changed
  - per change: a `summary` (list row), a `detail` paragraph (panel), and a
    `quote` (the actual new text on the page).

Jev already labelled severity; OpenAI only writes prose. Returns
(briefing, changes). No survivors -> ("", []) and no API call.
"""
import json
import httpx
from app.core.config import settings
from app.models.schemas import Change, ScoredChunk

OPENAI_URL = "https://api.openai.com/v1/chat/completions"

SYSTEM = (
    "You write a change digest for a website-monitoring tool. You are given a "
    "JSON array of changes, each with an index, the page it came from, and the "
    "old and new text. Produce a JSON object with two keys:\n"
    '  "briefing": a 2-3 sentence plain-English overview of what changed across '
    "all the pages, leading with the most consequential. Refer to pages by name.\n"
    '  "changes": an array, SAME length and order as the input, each an object '
    '{"index": <int>, "summary": "<one short sentence, the headline of this '
    'change>", "detail": "<a 2-4 sentence paragraph explaining what changed and '
    'why it may matter>", "quote": "<the key new text now on the page, quoted '
    'or lightly cleaned; if nothing quotable, a one-line description of the new '
    'content>"}.\n'
    "No preamble. Respond with ONLY the JSON object, nothing else."
)


def _fallback(survivors: list[ScoredChunk]) -> tuple[str, list[Change]]:
    changes = [
        Change(page_title=s.chunk.page_title, page_url=s.chunk.page_url,
               severity=s.verdict.severity,
               summary=(s.chunk.new_text[:120] or "Content changed"),
               detail=(s.chunk.new_text[:400] or "The page content changed."),
               quote=(s.chunk.new_text[:300] or ""),
               item_url=s.chunk.item_url)
        for s in survivors
    ]
    return ("Changes were detected across your watched pages.", changes)


async def summarise(survivors: list[ScoredChunk], openai_key: str) -> tuple[str, list[Change]]:
    if not survivors:
        return "", []

    rows = [
        {"index": i, "page": s.chunk.page_title,
         "old": s.chunk.old_text[:600], "new": s.chunk.new_text[:600]}
        for i, s in enumerate(survivors)
    ]
    payload = {
        "model": settings.openai_model,
        "messages": [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": json.dumps(rows)},
        ],
    }
    headers = {"Authorization": f"Bearer {openai_key}"}

    async with httpx.AsyncClient(timeout=90) as client:
        r = await client.post(OPENAI_URL, json=payload, headers=headers)
        r.raise_for_status()
        content = r.json()["choices"][0]["message"]["content"].strip()

    if content.startswith("```"):
        content = content.strip("`").lstrip("json").strip()

    try:
        obj = json.loads(content)
        briefing = str(obj.get("briefing", "")).strip()
        by_index = {int(it["index"]): it for it in obj.get("changes", [])}
    except (json.JSONDecodeError, KeyError, TypeError, ValueError):
        return _fallback(survivors)

    changes: list[Change] = []
    for i, s in enumerate(survivors):
        it = by_index.get(i, {})
        changes.append(Change(
            page_title=s.chunk.page_title,
            page_url=s.chunk.page_url,
            severity=s.verdict.severity,
            summary=(it.get("summary") or s.chunk.new_text[:120] or "Content changed"),
            detail=(it.get("detail") or ""),
            quote=(it.get("quote") or s.chunk.new_text[:300] or ""),
            item_url=s.chunk.item_url,
        ))
    return briefing, changes