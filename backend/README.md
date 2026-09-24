# Sentinel backend

FastAPI. The whole pipeline lives here. Deploys to Railway (Root Directory = `/backend`).

## Run the walking skeleton first

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m app.skeleton --mock      # zero keys, see the flow
cp .env.example .env               # add keys
python -m app.skeleton             # real Firecrawl + Jev on target #1
```

## Run the API

```bash
uvicorn app.main:app --reload
# POST http://localhost:8000/api/run    -> runs monitor, returns digest
# GET  http://localhost:8000/api/targets
# GET  http://localhost:8000/health
```

## Structure

```
app/
├── main.py            FastAPI app + CORS
├── skeleton.py        run-me-first proof (mock or real)
├── core/
│   ├── config.py      settings, thresholds, topic sentence (policy lives here)
│   └── targets.py     the list of pages to watch — edit this to add pages
├── services/
│   ├── scraper.py     Firecrawl scrape + git-diff  (swap for ClawEngine if needed)
│   ├── differ.py      git-diff -> paragraph chunks  (plain code, no model)
│   ├── jev.py         THE CORE — one typed decision per chunk
│   ├── summariser.py  the single OpenAI call, skipped when nothing survives
│   └── pipeline.py    wires the daily flow
├── routers/monitor.py /api/run, /api/targets
├── db/store.py        Neon layer — OFF by default (USE_DB=false)
└── models/schemas.py  Chunk, Verdict, the gate
```

## Deploy to Railway

1. Push repo to GitHub.
2. New Railway service → connect repo → set **Root Directory = `/backend`**.
3. Add env vars from `.env.example` (Railway auto-detects `$PORT`).
4. Set `ALLOWED_ORIGINS` to your Vercel URL.
