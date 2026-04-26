"""
Admin Config API — manage scoring weights and system config.
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import date, timedelta

from app.core.database import get_db
from app.core.security import require_roles
from app.models.models import AppConfig, AuditLog, User
from app.scoring.engine import ScoringEngine
from app.services.grouping import GroupingService
from app.ai.service import AnalysisService
from app.services.audit import log_audit

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/admin", tags=["Admin"])


@router.get("/configs")
def list_configs(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "lead")),
):
    """List all app configurations."""
    configs = db.query(AppConfig).order_by(AppConfig.config_key).all()
    return [
        {
            "id": c.id,
            "key": c.config_key,
            "value": c.config_value,
            "description": c.description,
            "updated_at": c.updated_at.isoformat() if c.updated_at else None,
        }
        for c in configs
    ]


class UpdateConfigRequest(BaseModel):
    value: dict | list | str | int | float
    description: Optional[str] = None


@router.put("/configs/{key}")
def update_config(
    key: str,
    req: UpdateConfigRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin")),
):
    """Create or update a configuration."""
    cfg = db.query(AppConfig).filter_by(config_key=key).first()
    old_value = cfg.config_value if cfg else None
    if cfg:
        cfg.config_value = req.value
        if req.description:
            cfg.description = req.description
    else:
        cfg = AppConfig(
            config_key=key,
            config_value=req.value,
            description=req.description or f"Config: {key}",
        )
        db.add(cfg)
        db.flush()

    log_audit(
        db,
        actor_id=current_user.id,
        action="admin.update_config",
        target_type="app_config",
        target_id=cfg.id,
        details={"key": key, "old_value": old_value, "new_value": req.value},
        ip_address=request.client.host if request.client else None,
    )
    db.commit()
    return {"key": key, "value": cfg.config_value, "message": "Updated"}


class RecalculateRequest(BaseModel):
    repo_id: Optional[int] = None
    period_days: int = 90
    rebuild_work_items: bool = False
    rerun_analysis: bool = False


@router.post("/recalculate")
def recalculate_all(
    req: RecalculateRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin")),
):
    """Full recalculate: optionally rebuild work items, rerun analysis, then recalculate scores."""
    from app.models.models import Repository

    results = {"steps": []}
    target_repo = None
    if req.repo_id is not None:
        target_repo = db.get(Repository, req.repo_id)
        if not target_repo:
            raise HTTPException(status_code=404, detail="Repository not found")

    # Step 1: Rebuild work items if requested
    if req.rebuild_work_items:
        repos = [target_repo] if target_repo else db.query(Repository).all()
        svc = GroupingService(db)
        for repo in repos:
            svc.clear_work_items_for_repo(repo.id)
            r = svc.build_work_items_for_repo(repo.id)
            results["steps"].append({"action": "build_work_items", "repo": repo.full_name, **r})

    # Step 2: Rerun analysis if requested
    if req.rerun_analysis:
        repos = [target_repo] if target_repo else db.query(Repository).all()
        asvc = AnalysisService(db)
        for repo in repos:
            r = asvc.analyze_repo(repo.id, force=True)
            results["steps"].append({"action": "analyze", "repo": repo.full_name, **r})

    # Step 3: Recalculate scores
    engine = ScoringEngine(db)
    period_end = date.today()
    period_start = period_end - timedelta(days=req.period_days)
    snaps = engine.calculate_all_scores(req.repo_id, period_start, period_end)
    results["steps"].append({
        "action": "calculate_scores",
        "developers_scored": len(snaps),
        "repo_id": req.repo_id,
        "repo": target_repo.full_name if target_repo else None,
        "period": f"{period_start} to {period_end}",
    })

    log_audit(
        db,
        actor_id=current_user.id,
        action="admin.recalculate",
        target_type="score_snapshots",
        details=req.model_dump(),
        ip_address=request.client.host if request.client else None,
    )
    db.commit()
    return results


@router.get("/system-info")
def system_info(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "lead")),
):
    """Return system overview stats."""
    from app.models.models import (
        Repository, Developer, Commit, PullRequest, Review,
        WorkItem, AICommitAnalysis, ScoreSnapshot,
    )

    return {
        "repositories": db.query(func.count(Repository.id)).scalar() or 0,
        "developers": db.query(func.count(Developer.id)).scalar() or 0,
        "commits": db.query(func.count(Commit.id)).scalar() or 0,
        "pull_requests": db.query(func.count(PullRequest.id)).scalar() or 0,
        "reviews": db.query(func.count(Review.id)).scalar() or 0,
        "work_items": db.query(func.count(WorkItem.id)).scalar() or 0,
        "ai_analyses": db.query(func.count(AICommitAnalysis.id)).scalar() or 0,
        "score_snapshots": db.query(func.count(ScoreSnapshot.id)).scalar() or 0,
        "users": db.query(func.count(User.id)).scalar() or 0,
        "audit_logs": db.query(func.count(AuditLog.id)).scalar() or 0,
    }


@router.get("/audit-logs")
def list_audit_logs(
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "lead")),
):
    logs = db.query(AuditLog).order_by(AuditLog.created_at.desc()).limit(limit).all()
    return [
        {
            "id": log.id,
            "actor_id": log.actor_id,
            "action": log.action,
            "target_type": log.target_type,
            "target_id": log.target_id,
            "details": log.details,
            "ip_address": log.ip_address,
            "created_at": log.created_at.isoformat() if log.created_at else None,
        }
        for log in logs
    ]
