"""The data that flows through the pipeline. One Chunk per changed paragraph;
one Verdict per Jev decision."""
from pydantic import BaseModel


class Chunk(BaseModel):
    """One changed paragraph: what Jev judges."""
    page_title: str
    page_url: str
    old_text: str
    new_text: str
    question: str          # per-target relevance question for Jev


class Verdict(BaseModel):
    """Jev's typed answer for one chunk.

    severity is a Choice (option + confidence, both from the distribution).
    relevant and is_noise are Nouls: a single probability of yes, 0..1, with
    NO separate confidence — the probability is the whole signal.
    """
    severity: str          # "high" | "medium" | "low"
    severity_conf: float   # Choice confidence, from the distribution
    relevant: float        # Noul: P(change is on-topic)
    is_noise: float        # Noul: P(change is purely cosmetic)

    def passes(self, sev_min: float, rel_min: float, noise_max: float) -> bool:
        """The gate. Plain code, not the model, decides what survives.

        A Noul is thresholded directly (docs: `noul > threshold`). A high
        is_noise probability drops the chunk; relevant must clear rel_min.
        Keeps high AND medium severity — medium catches genuinely new content
        of uncertain impact, which is worth surfacing for a monitor.
        """
        if self.is_noise >= noise_max:
            return False
        return (
            self.severity in ("high", "medium")
            and self.severity_conf >= sev_min
            and self.relevant >= rel_min
        )


class ScoredChunk(BaseModel):
    chunk: Chunk
    verdict: Verdict