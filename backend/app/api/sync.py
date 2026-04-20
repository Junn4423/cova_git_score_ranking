"""
Sync / Ingestion API endpoints.
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.core.database import get_db
from app.services.ingestion import IngestionService
from app.models.models import Repository, Developer, Commit, PullRequest, Review

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/sync", tags=["Sync"])


class SyncRepoRequest(BaseModel):
    full_name: str
    since: Optional[str] = None
    max_commit_pages: int = 3
    max_pr_pages: int = 2
    fetch_files: bool = True


class SyncRepoResponse(BaseModel):
    repo: str
    new_commits: int
    new_prs: int
    total_developers: int


@router.post("/repo", response_model=SyncRepoResponse)
def sync_single_repo(req: SyncRepoRequest, db: Session = Depends(get_db)):
    """Sync a single GitHub repository (repo + commits + PRs + reviews)."""
    try:
        svc = IngestionService(db)
        result = svc.full_sync_repo(
            full_name=req.full_name,
            since=req.since,
            max_commit_pages=req.max_commit_pages,
            max_pr_pages=req.max_pr_pages,
            fetch_files=req.fetch_files,
        )
        return SyncRepoResponse(**result)
    except Exception as e:
        logger.exception("Sync failed for %s", req.full_name)
        raise HTTPException(status_code=500, detail=str(e))


# ── Stats endpoints ─────────────────────────────────────────

class SyncStatsResponse(BaseModel):
    repositories: int
    developers: int
    commits: int
    pull_requests: int
    reviews: int


@router.get("/stats", response_model=SyncStatsResponse)
def get_sync_stats(db: Session = Depends(get_db)):
    """Return counts of synced data."""
    return SyncStatsResponse(
        repositories=db.query(Repository).count(),
        developers=db.query(Developer).count(),
        commits=db.query(Commit).count(),
        pull_requests=db.query(PullRequest).count(),
        reviews=db.query(Review).count(),
    )


# ── List endpoints ──────────────────────────────────────────

@router.get("/repositories")
def list_repositories(db: Session = Depends(get_db)):
    """List all synced repositories."""
    repos = db.query(Repository).order_by(Repository.full_name).all()
    return [
        {
            "id": r.id,
            "full_name": r.full_name,
            "name": r.name,
            "description": r.description,
            "default_branch": r.default_branch,
            "is_tracked": r.is_tracked,
            "last_synced_at": r.last_synced_at.isoformat() if r.last_synced_at else None,
        }
        for r in repos
    ]


@router.get("/developers")
def list_developers(db: Session = Depends(get_db)):
    """List all discovered developers."""
    devs = db.query(Developer).order_by(Developer.github_login).all()
    return [
        {
            "id": d.id,
            "github_login": d.github_login,
            "display_name": d.display_name,
            "email": d.email,
            "avatar_url": d.avatar_url,
            "is_bot": d.is_bot,
            "commit_count": db.query(Commit).filter_by(author_id=d.id).count(),
        }
        for d in devs
    ]


@router.get("/commits")
def list_commits(
    repo_id: Optional[int] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    """List recent commits, optionally filtered by repo."""
    q = db.query(Commit).order_by(Commit.committed_at.desc())
    if repo_id:
        q = q.filter(Commit.repo_id == repo_id)
    commits = q.limit(limit).all()
    return [
        {
            "id": c.id,
            "sha": c.sha,
            "message": (c.message or "")[:200],
            "author": c.author.github_login if c.author else c.raw_author_name,
            "committed_at": c.committed_at.isoformat() if c.committed_at else None,
            "additions": c.additions,
            "deletions": c.deletions,
            "is_merge": c.is_merge,
            "repo": c.repository.full_name,
        }
        for c in commits
    ]
