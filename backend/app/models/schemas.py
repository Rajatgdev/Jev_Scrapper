"""The data that flows through the pipeline. One Chunk per changed paragraph;
one Verdict per Jev decision; one Change per kept, summarised item."""
from pydantic import BaseModel


class Chunk(BaseModel):
    """One changed paragraph: what Jev judges."""
    page_title: str
    page_url: str
    old_text: str
    new_text: str
    question: str          # per-target relevance question for Jev
    item_url: str = ""     # direct link to the specific item (set by the differ)


class Verdict(BaseModel):
    """Jev's typed answer for one chunk.

    severity is a Choice (option + confidence). relevant and is_noise are Nouls:
    a single probability of yes, 0..1, no separate confidence.
    """
    severity: str          # "high" | "medium" | "low"
    severity_conf: float
    relevant: float        # Noul: P(change is on-topic)
    is_noise: float        # Noul: P(change is purely cosmetic)

    def keep(self, rel_min: float, noise_max: float) -> bool:
        """Sorter, not gate: keep any real, on-topic change regardless of
        severity. Drop only pure noise (cookie banners, timestamps) and
        off-topic changes. Severity is a LABEL for the kept item, not a filter.
        """
        if self.is_noise >= noise_max:
            return False
        return self.relevant >= rel_min


class ScoredChunk(BaseModel):
    chunk: Chunk
    verdict: Verdict


class Change(BaseModel):
    """A kept change, summarised for the digest/UI. Grouped by severity."""
    page_title: str
    page_url: str
    severity: str          # "high" | "medium" | "low"
    summary: str           # OpenAI one-liner (the list row)
    detail: str = ""       # OpenAI paragraph — "what changed" in the panel
    quote: str = ""        # the actual new text on the page (Option B)
    item_url: str = ""     # direct link to the item; empty -> fall back to page_url