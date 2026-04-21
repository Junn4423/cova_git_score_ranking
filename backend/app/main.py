"""
Engineering Contribution Analytics – FastAPI entry point.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.api.health import router as health_router
from app.api.sync import router as sync_router
from app.api.dashboard import router as dashboard_router
from app.api.developers import router as developers_router
from app.api.repositories import router as repositories_router
from app.api.pull_requests import router as pull_requests_router
from app.api.work_items import router as work_items_router
from app.api.scores import router as scores_router

app = FastAPI(
    title="Engineering Contribution Analytics",
    description="Internal tool for analyzing developer contributions from GitHub",
    version="0.3.0",
)

# CORS – allow the Vite dev server and any internal origin
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:5174", "http://localhost:3000", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ─────────────────────────────────────────────────
app.include_router(health_router, tags=["Health"])
app.include_router(sync_router)
app.include_router(dashboard_router)
app.include_router(developers_router)
app.include_router(repositories_router)
app.include_router(pull_requests_router)
app.include_router(work_items_router)
app.include_router(scores_router)
