"""THE CORE. One Jev evaluation per changed chunk.

Jev is not an LLM. It takes state (the old + new paragraph) plus typed questions
and returns typed answers with confidence — a Choice for severity, Booleans for
relevance and noise. It generates no prose. This is the many-calls, fast, cheap
job the whole project is built around.

The exact request shape depends on the Jev SDK/endpoint you use (direct API vs
Composio MCP). The HTTP call below is written against a typed-evaluation endpoint
that takes a shared `state` and named questions; adjust field names to match the
Jev API you connect to. The CONTRACT — three named questions, typed answers with
confidence — is what matters and stays fixed.
"""
import httpx
from app.core.config import settings
from app.models.schemas import Chunk, Verdict

JEV_URL = "https://api.typesafe.ai/v1/evaluate"  # adjust to your Jev endpoint

SEVERITY_Q = (
    "Rate how significant this change is to someone tracking regulatory "
    "obligations. high = a rule, rate, threshold, deadline or scope changed. "
    "medium = substantive new content, impact unclear. low = cosmetic, "
    "navigational, or boilerplate."
)
NOISE_Q = (
    "Is this change purely cosmetic (footer, date stamp, link order, cookie "
    "notice) with no change in meaning?"
)


def _state(chunk: Chunk) -> str:
    return (
        f"Page: {chunk.page_title} ({chunk.page_url})\n"
        f"OLD:\n{chunk.old_text}\n\n"
        f"NEW:\n{chunk.new_text}"
    )


async def evaluate(chunk: Chunk) -> Verdict:
    """Send one shared state + three typed questions in a single call."""
    payload = {
        "model": settings.jev_model,
        "state": _state(chunk),
        "questions": {
            "severity": {"type": "choice", "options": ["high", "medium", "low"],
                         "question": SEVERITY_Q},
            "relevant": {"type": "boolean", "question": settings.topic_question},
            "is_noise": {"type": "boolean", "question": NOISE_Q},
        },
    }
    headers = {"Authorization": f"Bearer {settings.jev_api_key}"}

    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(JEV_URL, json=payload, headers=headers)
        r.raise_for_status()
        ans = r.json()["answers"]

    return Verdict(
        severity=ans["severity"]["value"],
        severity_conf=ans["severity"]["confidence"],
        relevant=ans["relevant"]["value"],
        relevant_conf=ans["relevant"]["confidence"],
        is_noise=ans["is_noise"]["value"],
        is_noise_conf=ans["is_noise"]["confidence"],
    )
