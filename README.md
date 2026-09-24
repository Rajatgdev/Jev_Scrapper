# Sentinel

A Jev-driven website change monitor. Scrapes a fixed list of pages daily, detects what
changed, has **Jev** classify every change by severity + topic relevance, and emails a
ranked digest. Jev makes the many decisions; OpenAI wakes once to write the email.

See `docs/Sentinel-Architecture.docx` for the full design.

## Layout (isolated monorepo)

```
sentinel/
├── backend/     FastAPI app — the whole pipeline lives here. Deploys to Railway.
├── frontend/    Vite + React dashboard. Deploys to Vercel.
└── docs/        Architecture doc.
```

Frontend and backend deploy **independently**: Railway root dir = `/backend`,
Vercel root dir = `/frontend`. They talk over HTTP + CORS via env vars.

## Quick start (backend, the part that matters first)

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # fill in FIRECRAWL_API_KEY, JEV_API_KEY, OPENAI_API_KEY
python -m app.skeleton      # runs the walking skeleton on ONE url, prints verdicts
```

The skeleton proves the idea end-to-end before any server, email, or DB is wired.

## Database

Off by default. The `backend/app/db/` layer is stubbed. To turn on Neon Postgres,
set `DATABASE_URL` in `.env` and flip `USE_DB=true`. Nothing else changes.
