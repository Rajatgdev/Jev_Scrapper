"""THE CORE. One Jev evaluation per changed chunk.

Jev is not an LLM. It takes state (the old + new paragraph) plus typed questions
and returns typed answers — a Choice for severity, Nouls for relevance and noise.
It generates no prose. This is the many-calls, fast, cheap job the whole project
is built around.

Contract (docs.typesafe.ai/api):
  POST https://api.typesafe.ai/v1/systemone
  body: { state, model, questions{ id: {type, instructions, criteria?} } }
  Choice question -> answer has .choice + .confidence
  Noul question   -> answer has .noul (0..1), NO separate confidence
"""
import httpx
from app.core.config import settings
from app.models.schemas import Chunk, Verdict

JEV_URL = "https://api.typesafe.ai/v1/systemone"

SEVERITY_INSTRUCTIONS = (
    "Rate how significant this change is to someone tracking regulatory "
    "obligations."
)
SEVERITY_CRITERIA = {
    "high": "A rule, rate, threshold, deadline or scope changed.",
    "medium": "Substantive new content, impact unclear.",
    "low": "Cosmetic, navigational, or boilerplate.",
}
NOISE_INSTRUCTIONS = (
    "Is this change purely cosmetic (footer, date stamp, link order, cookie "
    "notice) with no change in meaning?"
)


def _state(chunk: Chunk) -> dict:
    return {
        "page_title": chunk.page_title,
        "page_url": chunk.page_url,
        "old_text": chunk.old_text,
        "new_text": chunk.new_text,
    }


async def evaluate(chunk: Chunk) -> Verdict:
    """Send one shared state + three typed questions in a single call."""
    payload = {
        "state": _state(chunk),
        "model": settings.jev_model,
        "questions": {
            "severity": {
                "type": "choice",
                "instructions": SEVERITY_INSTRUCTIONS,
                "criteria": SEVERITY_CRITERIA,
            },
            "relevant": {
                "type": "noul",
                "instructions": chunk.question,
            },
            "is_noise": {
                "type": "noul",
                "instructions": NOISE_INSTRUCTIONS,
            },
        },
    }
    headers = {"Authorization": f"Bearer {settings.jev_api_key}"}

    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(JEV_URL, json=payload, headers=headers)
        r.raise_for_status()
        ans = r.json()["answers"]

    return Verdict(
        severity=ans["severity"]["choice"],
        severity_conf=ans["severity"]["confidence"],
        relevant=ans["relevant"]["noul"],
        is_noise=ans["is_noise"]["noul"],
    )