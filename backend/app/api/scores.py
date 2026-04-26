"""
Scoring API endpoints — calculate, ranking, developer scores.
"""

import logging
from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import require_roles
from app.scoring.engine import ScoringEngine
from app.models.models import (
    ScoreSnapshot, ScoreBreakdown, Developer, Repository, User,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/scores", tags=["Scores"])


class CalculateRequest(BaseModel):
    developer_id: int | None = None  # None = all developers
    repo_id: int | None = None
    period_days: int = Field(default=30, ge=1, le=365)


@router.post("/calculate")
def calculate_scores(
    req: CalculateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "lead")),
):
    """Trigger score calculation for one or all developers."""
    engine = ScoringEngine(db)
    period_end = date.today()
    period_start = period_end - timedelta(days=req.period_days)
    repo = None
    if req.repo_id is not None:
        repo = db.get(Repository, req.repo_id)
        if not repo:
            raise HTTPException(status_code=404, detail="Repository not found")

    try:
        if req.developer_id:
            snap = engine.calculate_score(req.developer_id, req.repo_id, period_start, period_end)
            if not snap:
                return {"message": "No data for scoring", "snapshots": 0}
            return {
                "message": "Score calculated",
                "snapshots": 1,
                "score": float(snap.final_score),
                "repo_id": req.repo_id,
                "repo": repo.full_name if repo else None,
                "scope": repo.full_name if repo else "Toan he thong",
            }
        else:
            snaps = engine.calculate_all_scores(req.repo_id, period_start, period_end)
            return {
                "message": f"Scores calculated for {len(snaps)} developers",
                "snapshots": len(snaps),
                "period": f"{period_start} to {period_end}",
                "repo_id": req.repo_id,
                "repo": repo.full_name if repo else None,
                "scope": repo.full_name if repo else "Toan he thong",
            }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.exception("Scoring failed")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/ranking")
def get_ranking(
    repo_id: int | None = Query(None),
    period_days: int = Query(30, ge=1, le=365),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """Get developer ranking by final score for the most recent period."""
    period_end = date.today()
    period_start = period_end - timedelta(days=period_days)
    repo = None
    if repo_id is not None:
        repo = db.get(Repository, repo_id)
        if not repo:
            raise HTTPException(status_code=404, detail="Repository not found")

    query = db.query(ScoreSnapshot).filter(
        ScoreSnapshot.period_start == period_start,
        ScoreSnapshot.period_end == period_end,
    )
    if repo_id is None:
        query = query.filter(ScoreSnapshot.repo_id.is_(None))
    else:
        query = query.filter(ScoreSnapshot.repo_id == repo_id)

    snapshots = query.order_by(ScoreSnapshot.final_score.desc()).limit(limit).all()
    scope_label = repo.full_name if repo else "Toan he thong"

    return [
        {
            "rank": i + 1,
            "developer_id": s.developer_id,
            "repo_id": s.repo_id,
            "repo_full_name": s.repository.full_name if s.repository else None,
            "scope": scope_label,
            "period_start": s.period_start.isoformat() if s.period_start else None,
            "period_end": s.period_end.isoformat() if s.period_end else None,
            "github_login": s.developer.github_login if s.developer else None,
            "display_name": s.developer.display_name if s.developer else None,
            "avatar_url": s.developer.avatar_url if s.developer else None,
            "final_score": float(s.final_score) if s.final_score else 0,
            "activity_score": float(s.activity_score) if s.activity_score else 0,
            "quality_score": float(s.quality_score) if s.quality_score else 0,
            "impact_score": float(s.impact_score) if s.impact_score else 0,
            "confidence": float(s.confidence_score) if s.confidence_score else 0,
            "top_positive_reasons": s.top_positive_reasons or [],
            "top_negative_reasons": s.top_negative_reasons or [],
            "calculated_at": s.calculated_at.isoformat() if s.calculated_at else None,
        }
        for i, s in enumerate(snapshots)
    ]


@router.get("/{dev_id}")
def get_developer_score(
    dev_id: int,
    repo_id: int | None = Query(None),
    period_days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db),
):
    """Get score detail for a single developer."""
    dev = db.query(Developer).get(dev_id)
    if not dev:
        raise HTTPException(status_code=404, detail="Developer not found")

    period_end = date.today()
    period_start = period_end - timedelta(days=period_days)
    repo = None
    if repo_id is not None:
        repo = db.get(Repository, repo_id)
        if not repo:
            raise HTTPException(status_code=404, detail="Repository not found")

    query = db.query(ScoreSnapshot).filter(
        ScoreSnapshot.developer_id == dev_id,
        ScoreSnapshot.period_start == period_start,
        ScoreSnapshot.period_end == period_end,
    )
    if repo_id is None:
        query = query.filter(ScoreSnapshot.repo_id.is_(None))
    else:
        query = query.filter(ScoreSnapshot.repo_id == repo_id)

    snapshot = query.order_by(ScoreSnapshot.calculated_at.desc()).first()

    if not snapshot:
        return {
            "developer": dev.github_login,
            "repo_id": repo_id,
            "repo": repo.full_name if repo else None,
            "has_score": False,
            "message": "No score calculated for this period",
        }

    # Get breakdowns
    breakdowns = (
        db.query(ScoreBreakdown)
        .filter_by(snapshot_id=snapshot.id)
        .all()
    )

    return {
        "developer": dev.github_login,
        "repo_id": snapshot.repo_id,
        "repo": snapshot.repository.full_name if snapshot.repository else None,
        "has_score": True,
        "snapshot": {
            "id": snapshot.id,
            "repo_id": snapshot.repo_id,
            "repo": snapshot.repository.full_name if snapshot.repository else None,
            "period_start": snapshot.period_start.isoformat(),
            "period_end": snapshot.period_end.isoformat(),
            "final_score": float(snapshot.final_score) if snapshot.final_score else 0,
            "activity_score": float(snapshot.activity_score) if snapshot.activity_score else 0,
            "quality_score": float(snapshot.quality_score) if snapshot.quality_score else 0,
            "impact_score": float(snapshot.impact_score) if snapshot.impact_score else 0,
            "confidence": float(snapshot.confidence_score) if snapshot.confidence_score else 0,
            "top_positive_reasons": snapshot.top_positive_reasons or [],
            "top_negative_reasons": snapshot.top_negative_reasons or [],
            "evidence_links": snapshot.evidence_links or [],
            "calculated_at": snapshot.calculated_at.isoformat() if snapshot.calculated_at else None,
        },
        "breakdowns": [
            {
                "component": b.component,
                "raw_value": float(b.raw_value) if b.raw_value else 0,
                "weight": float(b.weight) if b.weight else 0,
                "weighted_value": float(b.weighted_value) if b.weighted_value else 0,
                "details": b.details,
            }
            for b in breakdowns
        ],
    }
