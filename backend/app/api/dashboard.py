"""
Dashboard API endpoints – overview stats, commit activity, top contributors.
"""

import logging
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, cast, Date

from app.core.database import get_db
from app.models.models import (
    Repository, Developer, Commit, PullRequest, Review, CommitFile,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])


def _date_filter(days: int):
    """Return a datetime N days ago from now (UTC)."""
    return datetime.utcnow() - timedelta(days=days)


@router.get("/overview")
def dashboard_overview(
    days: int = Query(30, ge=1, le=365),
    repo_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
):
    """
    Team overview dashboard – top contributors, summary stats,
    filtered by time window and optional repo.
    """
    since = _date_filter(days)

    # Base commit query with filters
    commit_q = db.query(Commit).filter(Commit.committed_at >= since)
    pr_q = db.query(PullRequest).filter(PullRequest.github_created_at >= since)
    review_q = db.query(Review).filter(Review.submitted_at >= since)

    if repo_id:
        commit_q = commit_q.filter(Commit.repo_id == repo_id)
        pr_q = pr_q.filter(PullRequest.repo_id == repo_id)
        # reviews need join through PR
        pr_ids = [p.id for p in pr_q.all()]
        review_q = review_q.filter(Review.pull_request_id.in_(pr_ids)) if pr_ids else review_q.filter(False)

    total_commits = commit_q.count()
    total_prs = pr_q.count()
    total_reviews = review_q.count()
    merged_prs = pr_q.filter(PullRequest.merged == True).count()

    # Total lines changed
    lines_added = commit_q.with_entities(func.coalesce(func.sum(Commit.additions), 0)).scalar()
    lines_deleted = commit_q.with_entities(func.coalesce(func.sum(Commit.deletions), 0)).scalar()

    # Active developers (have commits in period)
    active_devs = (
        commit_q
        .filter(Commit.author_id.isnot(None))
        .with_entities(func.count(func.distinct(Commit.author_id)))
        .scalar()
    )

    # Top contributors by commit count
    top_contributors_q = (
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
        .filter(Commit.committed_at >= since)
    )
    if repo_id:
        top_contributors_q = top_contributors_q.filter(Commit.repo_id == repo_id)

    top_contributors = (
        top_contributors_q
        .group_by(Developer.id)
        .order_by(func.count(Commit.id).desc())
        .limit(10)
        .all()
    )

    # Repo breakdown
    repo_stats = (
        db.query(
            Repository.id,
            Repository.full_name,
            func.count(Commit.id).label("commit_count"),
        )
        .join(Commit, Commit.repo_id == Repository.id)
        .filter(Commit.committed_at >= since)
        .group_by(Repository.id)
        .order_by(func.count(Commit.id).desc())
        .all()
    )

    return {
        "period_days": days,
        "total_commits": total_commits,
        "total_pull_requests": total_prs,
        "merged_pull_requests": merged_prs,
        "total_reviews": total_reviews,
        "lines_added": int(lines_added),
        "lines_deleted": int(lines_deleted),
        "active_developers": active_devs,
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
        "repo_breakdown": [
            {
                "id": r.id,
                "full_name": r.full_name,
                "commit_count": r.commit_count,
            }
            for r in repo_stats
        ],
    }


@router.get("/commit-activity")
def commit_activity(
    days: int = Query(30, ge=1, le=365),
    repo_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
):
    """Daily commit counts for chart visualization."""
    since = _date_filter(days)

    q = (
        db.query(
            cast(Commit.committed_at, Date).label("date"),
            func.count(Commit.id).label("count"),
            func.coalesce(func.sum(Commit.additions), 0).label("additions"),
            func.coalesce(func.sum(Commit.deletions), 0).label("deletions"),
        )
        .filter(Commit.committed_at >= since)
    )
    if repo_id:
        q = q.filter(Commit.repo_id == repo_id)

    results = q.group_by(cast(Commit.committed_at, Date)).order_by("date").all()

    return [
        {
            "date": r.date.isoformat() if r.date else None,
            "commits": r.count,
            "additions": int(r.additions),
            "deletions": int(r.deletions),
        }
        for r in results
    ]
