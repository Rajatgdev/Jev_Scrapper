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
    """Jev's typed answer for one chunk."""
    severity: str          # "high" | "medium" | "low"
    severity_conf: float
    relevant: bool
    relevant_conf: float
    is_noise: bool = False
    is_noise_conf: float = 0.0

    def passes(self, sev_min: float, rel_min: float, noise_min: float) -> bool:
        """The gate. Plain code, not the model, decides what survives."""
        if self.is_noise and self.is_noise_conf >= noise_min:
            return False
        return (
            self.severity == "high"
            and self.severity_conf >= sev_min
            and self.relevant
            and self.relevant_conf >= rel_min
        )


class ScoredChunk(BaseModel):
    chunk: Chunk
    verdict: Verdict
