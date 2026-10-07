"""Send the daily change digest via Brevo's transactional email API.

Design: "Evidence". A masthead, a briefing card, then one card per important
change (what changed, plus the actual new text from the page), then a compact
list of routine changes. Built from small functions that mirror the approved
mockup. Every dynamic value is HTML-escaped and every link is checked to be
http(s). Dark mode and phone layout are handled by the <style> block below.

Contract: POST https://api.brevo.com/v3/smtp/email, `api-key` header,
{sender{name,email}, to[{email}], subject, htmlContent}.
"""
import html as _html
from datetime import datetime, timezone
from email.utils import parseaddr

import httpx

from app.core.config import settings
from app.models.schemas import Change

BREVO_URL = "https://api.brevo.com/v3/smtp/email"

SERIF = "Georgia,'Times New Roman',serif"
SANS = "Arial,Helvetica,sans-serif"

MAX_SHOWN = 8            # items shown before the rest collapse into "view all"
MAX_LOW_SHOWN = 2        # routine items allowed once the list is truncated
MAX_HTML_BYTES = 90_000  # Gmail clips messages near 102 KB; stay well under

_SEV = {
    "high": {"k": "hi", "label": "High priority", "fg": "#A6362E", "bg": "#F6E9E7"},
    "medium": {"k": "me", "label": "Medium priority", "fg": "#8A6D1F", "bg": "#F5EEDD"},
    "low": {"k": "lo", "label": "Routine", "fg": "#3F6B4C", "bg": "#E8F0E9"},
}

_HEAD = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="light dark">
<meta name="supported-color-schemes" content="light dark">
<title>Sentinel daily digest</title>
<style>
  @media (max-width:620px) {
    .pad { padding-left:20px !important; padding-right:20px !important; }
    .h1 { font-size:28px !important; line-height:34px !important; }
    a.btn { display:block !important; width:auto !important; }
  }
  @media (prefers-color-scheme: dark) {
    .e-bg { background:#14202A !important; }
    .e-card { background:#1E2B36 !important; }
    .e-cardb { border-color:#33424F !important; }
    .e-tint { background:#1B2833 !important; }
    .e-tx { color:#F2F4F5 !important; }
    .e-tx2 { color:#B7C0C8 !important; }
    .e-ink { color:#A8C8EC !important; }
    a.e-link { color:#A8C8EC !important; }
    a.e-lowlink { color:#F2F4F5 !important; }
    .e-rule { border-color:#33424F !important; }
    .e-hi { color:#EDBBAC !important; }
    .e-me { color:#D9C37A !important; }
    .e-lo { color:#A8C8AF !important; }
    .e-hibg { background:#3A2723 !important; }
    .e-mebg { background:#372F1B !important; }
    .e-lobg { background:#223428 !important; }
    .e-dot { background:#A8C8AF !important; }
    .e-quote { background:#18232D !important; border-left-color:#A8C8EC !important; }
    .e-brief { background:#1E2B36 !important; border-left-color:#A8C8EC !important; }
    a.e-btn { background:#A8C8EC !important; color:#12293F !important; }
  }
</style>
</head>
"""


def _e(value) -> str:
    return _html.escape(str(value or ""), quote=True)


def _plural(n: int, one: str, many: str) -> str:
    return one if n == 1 else many


def _sev(c: Change) -> str:
    return c.severity if c.severity in _SEV else "low"


def _safe_url(*candidates) -> str:
    """First candidate that is an http(s) URL, else the app's own URL."""
    for url in candidates:
        if url and str(url).lower().startswith(("http://", "https://")):
            return str(url)
    return settings.app_url


def _pick(changes: list[Change], limit: int) -> tuple[list[Change], list[Change]]:
    """Up to `limit` items. Above that: every high, then medium, then at most
    MAX_LOW_SHOWN routine. Returns (shown, omitted)."""
    if len(changes) <= limit:
        return list(changes), []
    by = {s: [c for c in changes if _sev(c) == s] for s in _SEV}
    shown = list(by["high"])
    shown += by["medium"][: max(0, limit - len(shown))]
    shown += by["low"][: min(MAX_LOW_SHOWN, max(0, limit - len(shown)))]
    ids = {id(c) for c in shown}
    return shown, [c for c in changes if id(c) not in ids]


def _pill(sev: str) -> str:
    s = _SEV[sev]
    k, label, fg, bg = s["k"], s["label"], s["fg"], s["bg"]
    return (f'<span class="e-{k} e-{k}bg" style="display:inline-block;padding:3px 10px;'
            f'border-radius:999px;background:{bg};color:{fg};font:700 12px/18px {SANS}">{label}</span>')


def _h2(text: str) -> str:
    return (f'<p class="e-tx" style="margin:30px 0 12px;font:700 21px/28px {SERIF};'
            f'color:#24313D">{_e(text)}</p>')


def _evidence_card(c: Change) -> str:
    sev = _sev(c)
    url = _e(_safe_url(c.item_url, c.page_url))
    detail = (c.detail or "").strip()
    quote = (c.quote or "").strip()

    detail_html = (
        f'<div class="e-tx" style="font:15px/24px {SANS};color:#3B4651;margin:10px 0 0">{_e(detail)}</div>'
        if detail else "")
    quote_html = (
        '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="margin:14px 0 0"><tr>'
        '<td class="e-quote" style="background:#F3F1EA;border-left:3px solid #1B3A5B;'
        'padding:12px 16px;border-radius:0 6px 6px 0">'
        f'<div class="e-tx2" style="font:700 12px/18px {SANS};color:#59636D">On the page now</div>'
        f'<div class="e-tx" style="font:14px/22px {SERIF};color:#24313D;margin:4px 0 0">{_e(quote)}</div>'
        '</td></tr></table>'
        if quote else "")

    return (
        '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" class="e-card e-cardb" '
        'style="margin:0 0 16px;background:#FFFFFF;border:1px solid #E4E2D9;border-radius:12px">'
        '<tr><td style="padding:20px 22px">'
        + _pill(sev)
        + f'<div class="e-tx" style="margin:10px 0 0;font:700 20px/28px {SERIF};color:#24313D">{_e(c.summary)}</div>'
        + detail_html
        + quote_html
        + f'<div style="margin:14px 0 0"><span class="e-tx2" style="font:13px/20px {SANS};color:#59636D">{_e(c.page_title)}</span>'
        + f'&nbsp;&nbsp;<a class="e-link" href="{url}" target="_blank" rel="noreferrer" '
        + f'style="font:700 13px/20px {SANS};color:#1B3A5B;text-decoration:underline">Open the article</a></div>'
        + '</td></tr></table>'
    )


def _routine_panel(items: list[Change]) -> str:
    rows = []
    for n, c in enumerate(items):
        url = _e(_safe_url(c.item_url, c.page_url))
        top = "padding:16px 0 0" if n else "padding:15px 0 0"
        border = "border-top:1px solid #E1DED3;" if n else ""
        rows.append(
            f'<tr><td width="20" valign="top" style="{top}">'
            '<span class="e-dot" style="display:inline-block;width:8px;height:8px;border-radius:50%;background:#3F6B4C"></span></td>'
            f'<td class="e-rule" style="padding:11px 0;{border}">'
            f'<a class="e-lowlink" href="{url}" target="_blank" rel="noreferrer" '
            f'style="font:600 15px/22px {SANS};color:#24313D;text-decoration:underline">{_e(c.summary)}</a>'
            f'<div class="e-tx2" style="font:13px/20px {SANS};color:#59636D">{_e(c.page_title)}</div>'
            '</td></tr>'
        )
    return (
        '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" class="e-tint" '
        'style="background:#F2F0E8;border-radius:10px"><tr><td style="padding:4px 20px">'
        '<table role="presentation" width="100%" cellpadding="0" cellspacing="0">'
        + "".join(rows)
        + '</table></td></tr></table>'
    )


def _more_html(omitted: list[Change], total: int) -> str:
    if not omitted:
        return ""
    n = len(omitted)
    if all(_sev(c) == "low" for c in omitted):
        text = f"Plus {n} more routine {_plural(n, 'change', 'changes')}."
    else:
        text = f"{n} more {_plural(n, 'change is', 'changes are')} not shown here."
    app = _e(settings.app_url.rstrip("/"))
    return (f'<p class="e-tx2" style="margin:14px 0 0;font:14px/22px {SANS};color:#59636D">{text} '
            f'<a class="e-link" href="{app}/" target="_blank" rel="noreferrer" '
            f'style="color:#1B3A5B;text-decoration:underline">View all {total} changes</a></p>')


def _cta() -> str:
    app = _e(settings.app_url.rstrip("/"))
    return (f'<div style="margin:30px 0 0"><a class="e-btn btn" href="{app}/" target="_blank" rel="noreferrer" '
            f'style="display:inline-block;width:240px;text-align:center;background:#1B3A5B;color:#FFFFFF;'
            f'border-radius:6px;font:700 16px/50px {SANS};text-decoration:none">Open full digest</a></div>')


def _footer() -> str:
    app = _e(settings.app_url.rstrip("/"))
    why = "You're receiving this daily digest because you monitor pages with Sentinel."
    return (
        '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="margin:34px 0 0"><tr>'
        f'<td class="e-rule e-tx2" style="border-top:1px solid #DDDCD5;padding:20px 0 0;font:13px/20px {SANS};color:#59636D">'
        f'{why}<br>'
        f'<a class="e-tx2" href="{app}/targets" target="_blank" rel="noreferrer" '
        'style="display:inline-block;padding:10px 18px 4px 0;color:#59636D;text-decoration:underline">Manage watched pages</a>'
        f'<a class="e-tx2" href="{app}/settings" target="_blank" rel="noreferrer" '
        'style="display:inline-block;padding:10px 0 4px;color:#59636D;text-decoration:underline">Manage digest schedule</a>'
        '</td></tr></table>'
    )


def _counts(changes: list[Change]) -> dict:
    return {s: sum(1 for c in changes if _sev(c) == s) for s in _SEV}


def _subject(changes: list[Change]) -> str:
    counts = _counts(changes)
    total, high = len(changes), counts["high"]
    if high:
        return f"Sentinel: {high} high-priority {_plural(high, 'change', 'changes')}, {total} in total"
    return f"Sentinel: {total} {_plural(total, 'change', 'changes')} today, none high priority"


def _build_html(briefing: str, changes: list[Change], limit: int = MAX_SHOWN) -> str:
    counts = _counts(changes)
    shown, omitted = _pick(changes, limit)
    important = [c for c in shown if _sev(c) in ("high", "medium")]
    routine = [c for c in shown if _sev(c) == "low"]

    now = datetime.now(timezone.utc)
    date_text = f"{now.strftime('%A')} {now.day} {now.strftime('%B')}"
    preheader = (f"{counts['high']} high, {counts['medium']} medium, {counts['low']} routine. "
                 "Your watched pages, in order of importance.")

    parts = []
    if briefing:
        parts.append(
            '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" class="e-brief e-card e-cardb" '
            'style="background:#FFFFFF;border:1px solid #E4E2D9;border-left:4px solid #1B3A5B;'
            'border-radius:6px 12px 12px 6px"><tr><td style="padding:18px 22px">'
            f'<div class="e-tx" style="font:400 19px/29px {SERIF};color:#24313D">{_e(briefing)}</div>'
            '</td></tr></table>')
    if important:
        parts.append(_h2("What changed"))
        parts.extend(_evidence_card(c) for c in important)
    if routine:
        parts.append(_h2("Also changed"))
        parts.append(_routine_panel(routine))
    parts.append(_more_html(omitted, len(changes)))
    body = "".join(parts)

    return (
        _HEAD
        + '<body class="e-bg" style="margin:0;padding:0;background:#F5F4EF">'
        + f'<div style="display:none;max-height:0;overflow:hidden;opacity:0;mso-hide:all">{_e(preheader)}</div>'
        + '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" class="e-bg" '
          'style="background:#F5F4EF"><tr><td align="center">'
        + '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="max-width:600px">'
          '<tr><td class="pad" style="padding:30px 32px 36px">'
        + '<table role="presentation" width="100%" cellpadding="0" cellspacing="0"><tr>'
        + f'<td class="e-ink" style="font:700 22px/28px {SERIF};color:#1B3A5B">Sentinel</td>'
        + f'<td align="right" class="e-tx2" style="font:13px/18px {SANS};color:#59636D">{_e(date_text)}</td>'
        + '</tr></table>'
        + f'<h1 class="e-tx h1" style="margin:18px 0 0;font:400 34px/40px {SERIF};color:#24313D">Your daily digest</h1>'
        + f'<p class="e-tx2" style="margin:6px 0 20px;font:14px/22px {SANS};color:#59636D">'
          f'{counts["high"]} high, {counts["medium"]} medium, {counts["low"]} routine</p>'
        + body
        + _cta()
        + _footer()
        + '</td></tr></table></td></tr></table></body></html>'
    )


async def send_digest(briefing: str, changes: list[Change],
                      to: str | None = None) -> bool:
    """Send the digest email: briefing, evidence cards, routine list."""
    recipient = to or settings.digest_to
    if not (settings.brevo_api_key and recipient and settings.digest_from):
        raise RuntimeError(
            "Email not configured: set BREVO_API_KEY, DIGEST_FROM, and a recipient"
        )

    # Keep the message comfortably under Gmail's clipping limit: if it is too
    # big, show fewer items (the full list is always in the web digest).
    limit = MAX_SHOWN
    html_body = _build_html(briefing, changes, limit)
    while len(html_body.encode("utf-8")) > MAX_HTML_BYTES and limit > 2:
        limit -= 2
        html_body = _build_html(briefing, changes, limit)

    # DIGEST_FROM looks like: Sentinel <you@example.com>. Brevo wants the name
    # and email separately, and the email must be a verified Brevo sender.
    sender_name, sender_email = parseaddr(settings.digest_from)
    payload = {
        "sender": {"name": sender_name or "Sentinel", "email": sender_email},
        "to": [{"email": recipient}],
        "subject": _subject(changes),
        "htmlContent": html_body,
    }
    headers = {
        "api-key": settings.brevo_api_key,
        "accept": "application/json",
        "content-type": "application/json",
    }
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(BREVO_URL, json=payload, headers=headers)
        if r.status_code >= 400:
            print(f"    [email] brevo error {r.status_code}: {r.text[:300]}")
        r.raise_for_status()
    return True