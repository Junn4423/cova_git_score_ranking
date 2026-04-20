"""
Pull Request API endpoints – list with filters.
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.models import PullRequest, Review

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/pull-requests", tags=["Pull Requests"])


@router.get("")
def list_pull_requests(
    repo_id: Optional[int] = Query(None),
    author_id: Optional[int] = Query(None),
    state: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    """List pull requests with optional filters."""
    q = db.query(PullRequest).order_by(PullRequest.github_created_at.desc())

    if repo_id:
        q = q.filter(PullRequest.repo_id == repo_id)
    if author_id:
        q = q.filter(PullRequest.author_id == author_id)
    if state:
        if state == "merged":
            q = q.filter(PullRequest.merged == True)
        else:
            q = q.filter(PullRequest.state == state)

    prs = q.limit(limit).all()

    results = []
    for pr in prs:
        review_count = db.query(Review).filter_by(pull_request_id=pr.id).count()
        results.append({
            "id": pr.id,
            "number": pr.github_pr_number,
            "title": pr.title,
            "state": pr.state,
            "merged": pr.merged,
            "author": pr.author.github_login if pr.author else None,
            "author_avatar": pr.author.avatar_url if pr.author else None,
            "repo": pr.repository.full_name,
            "head_branch": pr.head_branch,
            "base_branch": pr.base_branch,
            "additions": pr.additions,
            "deletions": pr.deletions,
            "changed_files": pr.changed_files,
            "review_count": review_count,
            "created_at": pr.github_created_at.isoformat() if pr.github_created_at else None,
            "merged_at": pr.merged_at.isoformat() if pr.merged_at else None,
            "closed_at": pr.closed_at.isoformat() if pr.closed_at else None,
        })

    return results
