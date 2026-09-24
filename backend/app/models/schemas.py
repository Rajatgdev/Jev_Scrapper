"""The data that flows through the pipeline. One Chunk per changed paragraph;
one Verdict per Jev decision."""
from pydantic import BaseModel


class Chunk(BaseModel):
    """One changed paragraph: what Jev judges."""
    page_title: str
    page_url: str
    old_text: str
    new_text: str


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
        """
        if self.is_noise >= noise_max:
            return False
        return (
            self.severity == "high"
            and self.severity_conf >= sev_min
            and self.relevant >= rel_min
        )


class ScoredChunk(BaseModel):
    chunk: Chunk
    verdict: Verdict