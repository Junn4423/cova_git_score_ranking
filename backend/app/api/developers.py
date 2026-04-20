"""
Developer API endpoints – list, detail, commits, activity, aliases.
"""

import logging
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import func, cast, Date

from app.core.database import get_db
from app.models.models import (
    Developer, DeveloperAlias, Commit, PullRequest,
    Review, CommitFile,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/developers", tags=["Developers"])


@router.get("")
def list_developers(
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """List all developers with aggregated stats."""
    devs = db.query(Developer).order_by(Developer.github_login).all()

    results = []
    for d in devs:
        if search and search.lower() not in (d.github_login or "").lower() \
                and search.lower() not in (d.display_name or "").lower() \
                and search.lower() not in (d.email or "").lower():
            continue

        commit_count = db.query(func.count(Commit.id)).filter_by(author_id=d.id).scalar()
        pr_count = db.query(func.count(PullRequest.id)).filter_by(author_id=d.id).scalar()
        review_count = db.query(func.count(Review.id)).filter_by(reviewer_id=d.id).scalar()
        lines_added = (
            db.query(func.coalesce(func.sum(Commit.additions), 0))
            .filter_by(author_id=d.id)
            .scalar()
        )
        lines_deleted = (
            db.query(func.coalesce(func.sum(Commit.deletions), 0))
            .filter_by(author_id=d.id)
            .scalar()
        )

        results.append({
            "id": d.id,
            "github_login": d.github_login,
            "display_name": d.display_name,
            "email": d.email,
            "avatar_url": d.avatar_url,
            "is_bot": d.is_bot,
            "is_active": d.is_active,
            "commit_count": commit_count,
            "pr_count": pr_count,
            "review_count": review_count,
            "lines_added": int(lines_added),
            "lines_deleted": int(lines_deleted),
            "created_at": d.created_at.isoformat() if d.created_at else None,
        })

    return results


@router.get("/{dev_id}")
def get_developer(dev_id: int, db: Session = Depends(get_db)):
    """Get detailed info for a single developer."""
    dev = db.query(Developer).get(dev_id)
    if not dev:
        raise HTTPException(status_code=404, detail="Developer not found")

    commit_count = db.query(func.count(Commit.id)).filter_by(author_id=dev.id).scalar()
    pr_count = db.query(func.count(PullRequest.id)).filter_by(author_id=dev.id).scalar()
    review_count = db.query(func.count(Review.id)).filter_by(reviewer_id=dev.id).scalar()
    lines_added = (
        db.query(func.coalesce(func.sum(Commit.additions), 0))
        .filter_by(author_id=dev.id)
        .scalar()
    )
    lines_deleted = (
        db.query(func.coalesce(func.sum(Commit.deletions), 0))
        .filter_by(author_id=dev.id)
        .scalar()
    )

    # Active days (unique dates with commits)
    active_days = (
        db.query(func.count(func.distinct(cast(Commit.committed_at, Date))))
        .filter_by(author_id=dev.id)
        .scalar()
    )

    # Aliases
    aliases = db.query(DeveloperAlias).filter_by(developer_id=dev.id).all()

    # Recent commits (last 20)
    recent_commits = (
        db.query(Commit)
        .filter_by(author_id=dev.id)
        .order_by(Commit.committed_at.desc())
        .limit(20)
        .all()
    )

    # Recent PRs (last 10)
    recent_prs = (
        db.query(PullRequest)
        .filter_by(author_id=dev.id)
        .order_by(PullRequest.github_created_at.desc())
        .limit(10)
        .all()
    )

    # Recent reviews (last 10)
    recent_reviews = (
        db.query(Review)
        .filter_by(reviewer_id=dev.id)
        .order_by(Review.submitted_at.desc())
        .limit(10)
        .all()
    )

    return {
        "id": dev.id,
        "github_login": dev.github_login,
        "display_name": dev.display_name,
        "email": dev.email,
        "avatar_url": dev.avatar_url,
        "is_bot": dev.is_bot,
        "is_active": dev.is_active,
        "created_at": dev.created_at.isoformat() if dev.created_at else None,
        "stats": {
            "commit_count": commit_count,
            "pr_count": pr_count,
            "review_count": review_count,
            "lines_added": int(lines_added),
            "lines_deleted": int(lines_deleted),
            "active_days": active_days,
        },
        "aliases": [
            {
                "id": a.id,
                "alias_type": a.alias_type,
                "alias_value": a.alias_value,
            }
            for a in aliases
        ],
        "recent_commits": [
            {
                "id": c.id,
                "sha": c.sha,
                "message": (c.message or "")[:200],
                "committed_at": c.committed_at.isoformat() if c.committed_at else None,
                "additions": c.additions,
                "deletions": c.deletions,
                "is_merge": c.is_merge,
                "repo": c.repository.full_name,
            }
            for c in recent_commits
        ],
        "recent_prs": [
            {
                "id": pr.id,
                "number": pr.github_pr_number,
                "title": pr.title,
                "state": pr.state,
                "merged": pr.merged,
                "repo": pr.repository.full_name,
                "created_at": pr.github_created_at.isoformat() if pr.github_created_at else None,
            }
            for pr in recent_prs
        ],
        "recent_reviews": [
            {
                "id": r.id,
                "state": r.state,
                "submitted_at": r.submitted_at.isoformat() if r.submitted_at else None,
                "pr_title": r.pull_request.title if r.pull_request else None,
                "pr_number": r.pull_request.github_pr_number if r.pull_request else None,
                "repo": r.pull_request.repository.full_name if r.pull_request else None,
            }
            for r in recent_reviews
        ],
    }


@router.get("/{dev_id}/commits")
def developer_commits(
    dev_id: int,
    repo_id: Optional[int] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    """List commits by a developer."""
    dev = db.query(Developer).get(dev_id)
    if not dev:
        raise HTTPException(status_code=404, detail="Developer not found")

    q = db.query(Commit).filter_by(author_id=dev_id).order_by(Commit.committed_at.desc())
    if repo_id:
        q = q.filter(Commit.repo_id == repo_id)

    commits = q.limit(limit).all()
    return [
        {
            "id": c.id,
            "sha": c.sha,
            "message": (c.message or "")[:200],
            "committed_at": c.committed_at.isoformat() if c.committed_at else None,
            "additions": c.additions,
            "deletions": c.deletions,
            "is_merge": c.is_merge,
            "repo": c.repository.full_name,
        }
        for c in commits
    ]


@router.get("/{dev_id}/activity")
def developer_activity(
    dev_id: int,
    days: int = Query(90, ge=1, le=365),
    db: Session = Depends(get_db),
):
    """Daily commit activity for one developer (for chart)."""
    dev = db.query(Developer).get(dev_id)
    if not dev:
        raise HTTPException(status_code=404, detail="Developer not found")

    since = datetime.utcnow() - timedelta(days=days)
    results = (
        db.query(
            cast(Commit.committed_at, Date).label("date"),
            func.count(Commit.id).label("count"),
            func.coalesce(func.sum(Commit.additions), 0).label("additions"),
            func.coalesce(func.sum(Commit.deletions), 0).label("deletions"),
        )
        .filter(Commit.author_id == dev_id, Commit.committed_at >= since)
        .group_by(cast(Commit.committed_at, Date))
        .order_by("date")
        .all()
    )

    return [
        {
            "date": r.date.isoformat() if r.date else None,
            "commits": r.count,
            "additions": int(r.additions),
            "deletions": int(r.deletions),
        }
        for r in results
    ]


# ── Alias Management ────────────────────────────────────────

@router.get("/{dev_id}/aliases")
def list_aliases(dev_id: int, db: Session = Depends(get_db)):
    """List all aliases for a developer."""
    dev = db.query(Developer).get(dev_id)
    if not dev:
        raise HTTPException(status_code=404, detail="Developer not found")

    aliases = db.query(DeveloperAlias).filter_by(developer_id=dev_id).all()
    return [
        {
            "id": a.id,
            "alias_type": a.alias_type,
            "alias_value": a.alias_value,
            "created_at": a.created_at.isoformat() if a.created_at else None,
        }
        for a in aliases
    ]


class AddAliasRequest(BaseModel):
    alias_type: str  # "email" | "github_login" | "name"
    alias_value: str


@router.post("/{dev_id}/aliases")
def add_alias(dev_id: int, req: AddAliasRequest, db: Session = Depends(get_db)):
    """Add a new alias for a developer."""
    dev = db.query(Developer).get(dev_id)
    if not dev:
        raise HTTPException(status_code=404, detail="Developer not found")

    if req.alias_type not in ("email", "github_login", "name"):
        raise HTTPException(status_code=400, detail="alias_type must be email, github_login, or name")

    # Check if alias already exists
    existing = (
        db.query(DeveloperAlias)
        .filter_by(alias_type=req.alias_type, alias_value=req.alias_value)
        .first()
    )
    if existing:
        if existing.developer_id == dev_id:
            raise HTTPException(status_code=409, detail="Alias already exists for this developer")
        raise HTTPException(
            status_code=409,
            detail=f"Alias already assigned to developer #{existing.developer_id}"
        )

    alias = DeveloperAlias(
        developer_id=dev_id,
        alias_type=req.alias_type,
        alias_value=req.alias_value,
    )
    db.add(alias)
    db.commit()

    return {"message": "Alias added", "id": alias.id}


class MergeDevelopersRequest(BaseModel):
    keep_id: int
    merge_id: int


@router.post("/merge")
def merge_developers(req: MergeDevelopersRequest, db: Session = Depends(get_db)):
    """
    Merge two developers: re-assign all commits, PRs, reviews,
    and aliases from merge_id to keep_id, then deactivate merge_id.
    """
    if req.keep_id == req.merge_id:
        raise HTTPException(status_code=400, detail="Cannot merge a developer with themselves")

    keep_dev = db.query(Developer).get(req.keep_id)
    merge_dev = db.query(Developer).get(req.merge_id)

    if not keep_dev:
        raise HTTPException(status_code=404, detail=f"Developer #{req.keep_id} not found")
    if not merge_dev:
        raise HTTPException(status_code=404, detail=f"Developer #{req.merge_id} not found")

    # Re-assign commits
    db.query(Commit).filter_by(author_id=req.merge_id).update(
        {"author_id": req.keep_id}, synchronize_session=False
    )
    db.query(Commit).filter_by(committer_id=req.merge_id).update(
        {"committer_id": req.keep_id}, synchronize_session=False
    )

    # Re-assign PRs
    db.query(PullRequest).filter_by(author_id=req.merge_id).update(
        {"author_id": req.keep_id}, synchronize_session=False
    )

    # Re-assign reviews
    db.query(Review).filter_by(reviewer_id=req.merge_id).update(
        {"reviewer_id": req.keep_id}, synchronize_session=False
    )

    # Move aliases (skip duplicates)
    merge_aliases = db.query(DeveloperAlias).filter_by(developer_id=req.merge_id).all()
    for alias in merge_aliases:
        existing = (
            db.query(DeveloperAlias)
            .filter_by(
                developer_id=req.keep_id,
                alias_type=alias.alias_type,
                alias_value=alias.alias_value,
            )
            .first()
        )
        if existing:
            db.delete(alias)
        else:
            alias.developer_id = req.keep_id

    # Deactivate merged dev
    merge_dev.is_active = False
    db.commit()

    logger.info("Merged developer #%d into #%d", req.merge_id, req.keep_id)

    return {
        "message": f"Merged {merge_dev.github_login} into {keep_dev.github_login}",
        "keep_id": req.keep_id,
        "merged_id": req.merge_id,
    }
