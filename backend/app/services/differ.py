"""Turn a git-diff string into paragraph-level {old, new} chunks.

This is deterministic text code. No model. Don't pay Jev or OpenAI to do what
plain parsing does for free.

A git-diff groups lines: '-' removed, '+' added, ' ' unchanged. We pair each
run of removed lines with the following run of added lines into one Chunk. This
is a simple, good-enough v1 pairing; refine later if a source needs it.
"""
from app.models.schemas import Chunk


def chunks_from_diff(diff_text: str, page_title: str, page_url: str) -> list[Chunk]:
    chunks: list[Chunk] = []
    removed: list[str] = []
    added: list[str] = []

    def flush():
        old = " ".join(removed).strip()
        new = " ".join(added).strip()
        if old or new:
            chunks.append(Chunk(
                page_title=page_title, page_url=page_url,
                old_text=old, new_text=new,
            ))
        removed.clear()
        added.clear()

    for line in diff_text.splitlines():
        if line.startswith("@@") or line.startswith("+++") or line.startswith("---"):
            flush()  # hunk boundary
            continue
        if line.startswith("-"):
            removed.append(line[1:].strip())
        elif line.startswith("+"):
            added.append(line[1:].strip())
        else:  # context line ends the current change block
            flush()

    flush()
    return [c for c in chunks if c.old_text or c.new_text]
