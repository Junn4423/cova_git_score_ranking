"""
Repository API endpoints – list, detail, contributors, activity.
"""

import logging
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, cast, Date

from app.core.database import get_db
from app.models.models import (
    Repository, Developer, Commit, PullRequest, Review,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/repositories", tags=["Repositories"])


@router.get("")
def list_repositories(db: Session = Depends(get_db)):
    """List all repositories with aggregated stats."""
    repos = db.query(Repository).order_by(Repository.full_name).all()

    results = []
    for r in repos:
        commit_count = db.query(func.count(Commit.id)).filter_by(repo_id=r.id).scalar()
        pr_count = db.query(func.count(PullRequest.id)).filter_by(repo_id=r.id).scalar()
        contributor_count = (
            db.query(func.count(func.distinct(Commit.author_id)))
            .filter(Commit.repo_id == r.id, Commit.author_id.isnot(None))
            .scalar()
        )
        lines_added = (
            db.query(func.coalesce(func.sum(Commit.additions), 0))
            .filter_by(repo_id=r.id)
            .scalar()
        )
        lines_deleted = (
            db.query(func.coalesce(func.sum(Commit.deletions), 0))
            .filter_by(repo_id=r.id)
            .scalar()
        )

        results.append({
            "id": r.id,
            "github_id": r.github_id,
            "full_name": r.full_name,
            "name": r.name,
            "description": r.description,
            "default_branch": r.default_branch,
            "is_tracked": r.is_tracked,
            "exclude_from_ranking": r.exclude_from_ranking,
            "last_synced_at": r.last_synced_at.isoformat() if r.last_synced_at else None,
            "commit_count": commit_count,
            "pr_count": pr_count,
            "contributor_count": contributor_count,
            "lines_added": int(lines_added),
            "lines_deleted": int(lines_deleted),
        })

    return results


@router.get("/{repo_id}")
def get_repository(repo_id: int, db: Session = Depends(get_db)):
    """Get detailed info for a single repository."""
    repo = db.query(Repository).get(repo_id)
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")

    commit_count = db.query(func.count(Commit.id)).filter_by(repo_id=repo.id).scalar()
    pr_count = db.query(func.count(PullRequest.id)).filter_by(repo_id=repo.id).scalar()
    merged_pr_count = (
        db.query(func.count(PullRequest.id))
        .filter_by(repo_id=repo.id, merged=True)
        .scalar()
    )
    review_count = (
        db.query(func.count(Review.id))
        .join(PullRequest)
        .filter(PullRequest.repo_id == repo.id)
        .scalar()
    )

    lines_added = (
        db.query(func.coalesce(func.sum(Commit.additions), 0))
        .filter_by(repo_id=repo.id)
        .scalar()
    )
    lines_deleted = (
        db.query(func.coalesce(func.sum(Commit.deletions), 0))
        .filter_by(repo_id=repo.id)
        .scalar()
    )

    # Top contributors
    top_contributors = (
        db.query(
            Developer.id,
            Developer.github_login,
            Developer.display_name,
            Developer.avatar_url,
            func.count(Commit.id).label("commit_count"),
            func.coalesce(func.sum(Commit.additions), 0).label("additions"),
            func.coalesce(func.sum(Commit.deletions), 0).label("deletions"),
        )
        .join(Commit, Commit.author_id == Developer.id)
        .filter(Commit.repo_id == repo.id)
        .group_by(Developer.id)
        .order_by(func.count(Commit.id).desc())
        .limit(10)
        .all()
    )

    # Recent commits
    recent_commits = (
        db.query(Commit)
        .filter_by(repo_id=repo.id)
        .order_by(Commit.committed_at.desc())
        .limit(20)
        .all()
    )

    # Recent PRs
    recent_prs = (
        db.query(PullRequest)
        .filter_by(repo_id=repo.id)
        .order_by(PullRequest.github_created_at.desc())
        .limit(10)
        .all()
    )

    # Commit activity (last 30 days)
    since = datetime.utcnow() - timedelta(days=30)
    activity = (
        db.query(
            cast(Commit.committed_at, Date).label("date"),
            func.count(Commit.id).label("count"),
        )
        .filter(Commit.repo_id == repo.id, Commit.committed_at >= since)
        .group_by(cast(Commit.committed_at, Date))
        .order_by("date")
        .all()
    )

    return {
        "id": repo.id,
        "github_id": repo.github_id,
        "full_name": repo.full_name,
        "name": repo.name,
        "description": repo.description,
        "default_branch": repo.default_branch,
        "is_tracked": repo.is_tracked,
        "last_synced_at": repo.last_synced_at.isoformat() if repo.last_synced_at else None,
        "stats": {
            "commit_count": commit_count,
            "pr_count": pr_count,
            "merged_pr_count": merged_pr_count,
            "review_count": review_count,
            "lines_added": int(lines_added),
            "lines_deleted": int(lines_deleted),
        },
        "top_contributors": [
            {
                "id": c.id,
                "github_login": c.github_login,
                "display_name": c.display_name,
                "avatar_url": c.avatar_url,
                "commit_count": c.commit_count,
                "additions": int(c.additions),
                "deletions": int(c.deletions),
            }
            for c in top_contributors
        ],
        "recent_commits": [
            {
                "id": c.id,
                "sha": c.sha,
                "message": (c.message or "")[:200],
                "author": c.author.github_login if c.author else c.raw_author_name,
                "committed_at": c.committed_at.isoformat() if c.committed_at else None,
                "additions": c.additions,
                "deletions": c.deletions,
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
                "author": pr.author.github_login if pr.author else None,
                "created_at": pr.github_created_at.isoformat() if pr.github_created_at else None,
            }
            for pr in recent_prs
        ],
        "commit_activity": [
            {"date": a.date.isoformat() if a.date else None, "commits": a.count}
            for a in activity
        ],
    }
