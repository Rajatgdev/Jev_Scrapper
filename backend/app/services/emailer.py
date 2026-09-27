"""Send the daily digest via Resend's HTTP API. Plain httpx, no SDK.

Contract (resend.com/docs/api-reference/emails):
  POST https://api.resend.com/emails
  headers: Authorization: Bearer re_...
  body: { from, to: [..], subject, html }
"""
import httpx
from app.core.config import settings

RESEND_URL = "https://api.resend.com/emails"


def _html(digest: str) -> str:
    """Wrap the plain-text digest in minimal HTML (Resend wants html)."""
    body = digest.replace("\n", "<br>")
    return (
        "<div style=\"font-family:system-ui,sans-serif;max-width:640px;"
        "line-height:1.5\">"
        "<h2 style=\"color:#0f3460\">Sentinel — daily change digest</h2>"
        f"<div>{body}</div>"
        "<hr style=\"border:none;border-top:1px solid #ddd;margin:24px 0\">"
        "<p style=\"color:#777;font-size:13px\">Sent by Sentinel. "
        "Changes classified by Jev.</p></div>"
    )


async def send_digest(digest: str, survivor_count: int,
                      to: str | None = None) -> bool:
    """Send the digest email. Returns True on success.

    `to` is the recipient; defaults to settings.digest_to for the single-user
    manual path. The scheduler passes each user's own email.

    Caller decides whether to send; this just sends. Fails loud if the
    config is incomplete, so a misconfigured run doesn't silently skip.
    """
    recipient = to or settings.digest_to
    if not (settings.resend_api_key and recipient and settings.digest_from):
        raise RuntimeError(
            "Email not configured: set RESEND_API_KEY, DIGEST_FROM, and a recipient"
        )

    subject = (
        f"Sentinel: {survivor_count} significant change(s)"
        if survivor_count else "Sentinel: no significant changes today"
    )
    payload = {
        "from": settings.digest_from,
        "to": [recipient],
        "subject": subject,
        "html": _html(digest),
    }
    headers = {"Authorization": f"Bearer {settings.resend_api_key}"}

    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(RESEND_URL, json=payload, headers=headers)
        r.raise_for_status()
    return True