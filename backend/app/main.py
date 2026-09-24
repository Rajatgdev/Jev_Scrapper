"""FastAPI entry point. Deploys to Railway (root dir = /backend).
Start command: uvicorn app.main:app --host 0.0.0.0 --port $PORT
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.routers import monitor

app = FastAPI(title="Sentinel", version="1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(monitor.router)


@app.get("/health")
def health():
    return {"status": "ok"}
