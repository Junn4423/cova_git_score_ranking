"""
Engineering Contribution Analytics – FastAPI entry point.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.api.health import router as health_router
from app.api.sync import router as sync_router

app = FastAPI(
    title="Engineering Contribution Analytics",
    description="Internal tool for analyzing developer contributions from GitHub",
    version="0.1.0",
)

# CORS – allow the Vite dev server and any internal origin
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ─────────────────────────────────────────────────
app.include_router(health_router, tags=["Health"])
app.include_router(sync_router)
