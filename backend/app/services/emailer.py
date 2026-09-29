"""Send the change digest via Resend. Shows all changes grouped High/Med/Low,
each a one-line summary, with a button to open the full digest in the app.

Contract: POST https://api.resend.com/emails, Bearer auth, {from,to,subject,html}.
"""
import html as _html
import httpx
from app.core.config import settings
from app.models.schemas import Change

RESEND_URL = "https://api.resend.com/emails"

SEV = {
    "high":   ("High",   "#A6362E", "#F6E9E7"),
    "medium": ("Medium", "#8A6D1F", "#F5EEDD"),
    "low":    ("Low",    "#3F6B4C", "#E8F0E9"),
}


def _section(label: str, colour: str, bg: str, items: list[Change]) -> str:
    if not items:
        return ""
    rows = "".join(
        f'<div style="padding:10px 0;border-bottom:1px solid #eee">'
        f'<div style="font-size:14px;color:#1c1c1a">{_html.escape(c.summary)}</div>'
        f'<div style="font-size:12px;color:#8a8f98;margin-top:2px">'
        f'{_html.escape(c.page_title)}</div></div>'
        for c in items
    )
    return (
        f'<div style="margin:20px 0 8px">'
        f'<span style="display:inline-block;font-size:12px;font-weight:600;'
        f'color:{colour};background:{bg};padding:3px 10px;border-radius:20px">'
        f'{label} · {len(items)}</span></div>{rows}'
    )


def _build_html(briefing: str, changes: list[Change], counts: dict) -> str:
    buckets = {k: [c for c in changes if c.severity == k] for k in SEV}
    sections = "".join(
        _section(*SEV[k], buckets[k]) for k in ("high", "medium", "low")
    )
    digest_link = f"{settings.app_url.rstrip('/')}/digest"
    brief_html = (
        f'<div style="border:1px solid #E4E4DD;background:#fff;border-radius:12px;'
        f'padding:18px 20px;margin:6px 0 22px">'
        f'<p style="font-size:11px;font-weight:600;letter-spacing:.04em;'
        f'text-transform:uppercase;color:#8a8f98;margin:0 0 8px">Briefing</p>'
        f'<p style="font-family:Georgia,serif;font-size:16px;line-height:1.55;'
        f'color:#1c1c1a;margin:0">{briefing}</p></div>'
    ) if briefing else ""
    return (
        '<div style="font-family:system-ui,sans-serif;max-width:640px;'
        'line-height:1.5;color:#1c1c1a">'
        '<h2 style="font-family:Georgia,serif;color:#1b3a5b;font-weight:500">'
        'Sentinel — change digest</h2>'
        f'<p style="color:#5a5f6b;font-size:14px">'
        f'{counts["high"]} high · {counts["medium"]} medium · {counts["low"]} low</p>'
        f'{brief_html}'
        f'{sections}'
        f'<div style="margin-top:28px">'
        f'<a href="{digest_link}" style="display:inline-block;background:#1b3a5b;'
        f'color:#fff;text-decoration:none;font-size:14px;font-weight:500;'
        f'padding:11px 20px;border-radius:9px">Open full digest</a></div>'
        '<hr style="border:none;border-top:1px solid #ddd;margin:24px 0">'
        '<p style="color:#777;font-size:13px">Sent by Sentinel. '
        'Changes classified by Jev.</p></div>'
    )


async def send_digest(briefing: str, changes: list[Change],
                      to: str | None = None) -> bool:
    """Send the digest email: briefing + all changes grouped by severity."""
    recipient = to or settings.digest_to
    if not (settings.resend_api_key and recipient and settings.digest_from):
        raise RuntimeError(
            "Email not configured: set RESEND_API_KEY, DIGEST_FROM, and a recipient"
        )
    counts = {k: sum(c.severity == k for c in changes) for k in SEV}
    total = len(changes)
    subject = (f"Sentinel: {total} change(s) — "
               f"{counts['high']} high, {counts['medium']} med, {counts['low']} low")

    payload = {
        "from": settings.digest_from,
        "to": [recipient],
        "subject": subject,
        "html": _build_html(briefing, changes, counts),
    }
    headers = {"Authorization": f"Bearer {settings.resend_api_key}"}
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(RESEND_URL, json=payload, headers=headers)
        r.raise_for_status()
    return True