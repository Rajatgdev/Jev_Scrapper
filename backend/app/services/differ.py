"""Turn a git-diff string into paragraph-level {old, new} chunks.

This is deterministic text code. No model. Don't pay Jev or OpenAI to do what
plain parsing does for free.

A git-diff groups lines: '-' removed, '+' added, ' ' unchanged. We pair each
run of removed lines with the following run of added lines into one Chunk.

Each chunk also carries `item_url`: the direct link to the specific item it
describes. Firecrawl diffs the page's MARKDOWN, so an added line keeps its
[headline](url) syntax and we can read the URL straight out of it. If no usable
link is present we fall back to the watched page's URL.
"""
import re
from urllib.parse import urljoin, urldefrag

from app.models.schemas import Chunk

# inline link opener; the negative lookbehind skips image syntax ![alt](src)
_LINK_OPEN = re.compile(r"(?<!!)\[([^\]\n]+)\]\(")
_SKIP_PREFIXES = ("#", "mailto:", "javascript:", "tel:", "data:")
_IMAGE_EXT = (".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".ico")
_DECOR = " \t#*_>-"   # markdown decoration around a headline (###, **, bullets)


def _markdown_links(line: str):
    """Yield (anchor, dest, start, end) for each inline [text](dest) link."""
    for m in _LINK_OPEN.finditer(line):
        if m.group(1).startswith("!"):      # [![img](src)](href): skip the image
            continue
        i = m.end()
        while i < len(line) and line[i] == " ":
            i += 1
        if i >= len(line):
            continue
        if line[i] == "<":                  # [text](<url with spaces>)
            j = line.find(">", i + 1)
            if j < 0:
                continue
            dest = line[i + 1:j]
        else:                               # [text](url) or [text](url "title")
            j, depth = i, 0
            while j < len(line):
                c = line[j]
                if c == "\\":
                    j += 2
                    continue
                if c == "(":
                    depth += 1
                elif c == ")":
                    if depth == 0:
                        break
                    depth -= 1
                elif c.isspace() and depth == 0:
                    break
                j += 1
            dest = line[i:j]
        close = line.find(")", j)
        if close < 0 or not dest.strip():
            continue
        yield m.group(1), dest.strip(), m.start(), close + 1


def pick_item_url(lines: list[str], page_url: str) -> str:
    """Best single link for a changed chunk, or page_url as the safe fallback.

    On listing pages the headline row is usually a line that is ONLY a link,
    while byline rows mix text and links ("9:07 - 1 Oct - [Department](...)").
    So a link-only line wins; otherwise the first usable link in the chunk.
    Skips images, #fragments, mailto/javascript/tel/data links, and links that
    point back at the watched page itself.
    """
    page = urldefrag(page_url)[0].rstrip("/")
    only_link: list[str] = []
    any_link: list[str] = []
    for line in lines:
        for _anchor, dest, start, end in _markdown_links(line):
            if dest.lower().startswith(_SKIP_PREFIXES):
                continue
            url = urljoin(page_url, dest)
            if not url.lower().startswith(("http://", "https://")):
                continue
            clean = urldefrag(url)[0]
            if clean.rstrip("/") == page:
                continue
            if clean.lower().split("?")[0].endswith(_IMAGE_EXT):
                continue
            alone = (not line[:start].strip(_DECOR)) and (not line[end:].strip(_DECOR))
            (only_link if alone else any_link).append(url)
    if only_link:
        return only_link[0]
    if any_link:
        return any_link[0]
    return page_url


def chunks_from_diff(diff_text: str, page_title: str, page_url: str,
                     question: str) -> list[Chunk]:
    chunks: list[Chunk] = []
    removed: list[str] = []
    added: list[str] = []

    def flush():
        old = " ".join(removed).strip()
        new = " ".join(added).strip()
        if old or new:
            item_url = pick_item_url(added, page_url)
            print(f"    [differ] item_url={item_url}")
            chunks.append(Chunk(
                page_title=page_title, page_url=page_url,
                old_text=old, new_text=new, question=question,
                item_url=item_url,
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