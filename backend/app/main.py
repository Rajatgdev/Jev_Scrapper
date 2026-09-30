"""FastAPI entry point. Deploys to Railway (root dir = /backend).
Start command: uvicorn app.main:app --host 0.0.0.0 --port $PORT
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from app.core.config import settings
from app.routers import monitor
from app.routers import keys as keys_router
from app.auth.router import router as auth_router
from app.db.session import SessionLocal

app = FastAPI(title="Sentinel", version="1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(monitor.router)
app.include_router(keys_router.router)


@app.get("/health")
async def health():
    """Reports app health and whether the database is reachable."""
    db_ok = False
    try:
        async with SessionLocal() as s:
            await s.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        db_ok = False
    return {"status": "ok", "database": "connected" if db_ok else "unreachable"}