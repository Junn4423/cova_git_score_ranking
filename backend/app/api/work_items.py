"""
Work Items API endpoints — build, list, detail, stats.
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.core.database import get_db
from app.services.grouping import GroupingService
from app.models.models import (
    WorkItem, WorkItemCommit, Commit, Repository, Developer,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/work-items", tags=["Work Items"])


class BuildWorkItemsRequest(BaseModel):
    repo_id: int
    rebuild: bool = False


@router.post("/build")
def build_work_items(req: BuildWorkItemsRequest, db: Session = Depends(get_db)):
    """Trigger work item grouping for a repository."""
    try:
        svc = GroupingService(db)
        if req.rebuild:
            svc.clear_work_items_for_repo(req.repo_id)
        result = svc.build_work_items_for_repo(req.repo_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.exception("Failed to build work items for repo #%d", req.repo_id)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
def work_item_stats(db: Session = Depends(get_db)):
    """Return summary stats for work items."""
    total = db.query(func.count(WorkItem.id)).scalar()
    by_method = (
        db.query(
            WorkItem.grouping_method,
            func.count(WorkItem.id),
        )
        .group_by(WorkItem.grouping_method)
        .all()
    )
    return {
        "total_work_items": total,
        "by_method": {m: c for m, c in by_method},
    }


@router.get("")
def list_work_items(
    repo_id: Optional[int] = Query(None),
    developer_id: Optional[int] = Query(None),
    grouping_method: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """List work items with filters."""
    q = db.query(WorkItem).order_by(WorkItem.end_time.desc())

    if repo_id:
        q = q.filter(WorkItem.repo_id == repo_id)
    if developer_id:
        q = q.filter(WorkItem.developer_id == developer_id)
    if grouping_method:
        q = q.filter(WorkItem.grouping_method == grouping_method)

    total = q.count()
    items = q.offset(offset).limit(limit).all()

    return {
        "total": total,
        "items": [
            {
                "id": wi.id,
                "title": wi.title,
                "developer": wi.developer.github_login if wi.developer else None,
                "developer_id": wi.developer_id,
                "developer_avatar": wi.developer.avatar_url if wi.developer else None,
                "repo": wi.repository.full_name if wi.repository else None,
                "repo_id": wi.repo_id,
                "pr_number": wi.pull_request.github_pr_number if wi.pull_request else None,
                "grouping_method": wi.grouping_method,
                "commit_count": wi.commit_count,
                "total_additions": wi.total_additions,
                "total_deletions": wi.total_deletions,
                "file_count": wi.file_count,
                "start_time": wi.start_time.isoformat() if wi.start_time else None,
                "end_time": wi.end_time.isoformat() if wi.end_time else None,
            }
            for wi in items
        ],
    }


@router.get("/{item_id}")
def get_work_item(item_id: int, db: Session = Depends(get_db)):
    """Get detail for a single work item including commits."""
    wi = db.query(WorkItem).get(item_id)
    if not wi:
        raise HTTPException(status_code=404, detail="Work item not found")

    # Get linked commits
    wi_commits = (
        db.query(WorkItemCommit)
        .filter_by(work_item_id=wi.id)
        .all()
    )
    commit_ids = [wc.commit_id for wc in wi_commits]
    commits = (
        db.query(Commit)
        .filter(Commit.id.in_(commit_ids))
        .order_by(Commit.committed_at.asc())
        .all()
    ) if commit_ids else []

    return {
        "id": wi.id,
        "title": wi.title,
        "developer": {
            "id": wi.developer.id,
            "github_login": wi.developer.github_login,
            "display_name": wi.developer.display_name,
            "avatar_url": wi.developer.avatar_url,
        } if wi.developer else None,
        "repo": {
            "id": wi.repository.id,
            "full_name": wi.repository.full_name,
        } if wi.repository else None,
        "pull_request": {
            "id": wi.pull_request.id,
            "number": wi.pull_request.github_pr_number,
            "title": wi.pull_request.title,
        } if wi.pull_request else None,
        "grouping_method": wi.grouping_method,
        "commit_count": wi.commit_count,
        "total_additions": wi.total_additions,
        "total_deletions": wi.total_deletions,
        "file_count": wi.file_count,
        "start_time": wi.start_time.isoformat() if wi.start_time else None,
        "end_time": wi.end_time.isoformat() if wi.end_time else None,
        "commits": [
            {
                "id": c.id,
                "sha": c.sha,
                "message": (c.message or "")[:300],
                "author": c.author.github_login if c.author else c.raw_author_name,
                "committed_at": c.committed_at.isoformat() if c.committed_at else None,
                "additions": c.additions,
                "deletions": c.deletions,
                "is_merge": c.is_merge,
            }
            for c in commits
        ],
    }
