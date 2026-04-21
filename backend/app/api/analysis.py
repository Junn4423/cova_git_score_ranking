"""
AI Analysis API — run analysis, list results, stats.
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.core.database import get_db
from app.ai.service import AnalysisService
from app.models.models import AICommitAnalysis, Commit, Repository

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/analysis", tags=["AI Analysis"])


class RunAnalysisRequest(BaseModel):
    repo_id: int
    force: bool = False


class AnalyzeSingleRequest(BaseModel):
    commit_id: int
    force: bool = False


@router.post("/run")
def run_analysis(req: RunAnalysisRequest, db: Session = Depends(get_db)):
    """Trigger AI analysis for all commits in a repository."""
    try:
        svc = AnalysisService(db)
        result = svc.analyze_repo(req.repo_id, force=req.force)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.exception("Analysis failed")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/analyze-commit")
def analyze_single_commit(req: AnalyzeSingleRequest, db: Session = Depends(get_db)):
    """Analyze a single commit."""
    try:
        svc = AnalysisService(db)
        result = svc.analyze_single(req.commit_id, force=req.force)
        if not result:
            return {"message": "Already analyzed", "commit_id": req.commit_id}
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/stats")
def analysis_stats(db: Session = Depends(get_db)):
    """Return analysis summary statistics."""
    svc = AnalysisService(db)
    return svc.get_stats()


@router.get("/results")
def list_results(
    repo_id: Optional[int] = Query(None),
    change_type: Optional[str] = Query(None),
    min_complexity: Optional[int] = Query(None),
    min_risk: Optional[int] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """List analysis results with filters."""
    q = (
        db.query(AICommitAnalysis, Commit)
        .join(Commit, Commit.id == AICommitAnalysis.target_id)
        .filter(AICommitAnalysis.target_type == "commit")
    )

    if repo_id:
        q = q.filter(Commit.repo_id == repo_id)
    if change_type:
        q = q.filter(AICommitAnalysis.change_type == change_type)
    if min_complexity:
        q = q.filter(AICommitAnalysis.complexity_score >= min_complexity)
    if min_risk:
        q = q.filter(AICommitAnalysis.risk_score >= min_risk)

    total = q.count()
    rows = (
        q.order_by(AICommitAnalysis.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    return {
        "total": total,
        "items": [
            {
                "id": a.id,
                "commit_id": c.id,
                "sha": c.sha[:8],
                "message": (c.message or "")[:200],
                "author": c.author.github_login if c.author else c.raw_author_name,
                "author_avatar": c.author.avatar_url if c.author else None,
                "repo": c.repository.full_name if c.repository else None,
                "change_type": a.change_type,
                "summary": a.summary,
                "complexity_score": a.complexity_score,
                "risk_score": a.risk_score,
                "message_alignment_score": a.message_alignment_score,
                "test_presence": a.test_presence,
                "confidence": float(a.confidence) if a.confidence else 0,
                "notes": a.notes,
                "model_version": a.model_version,
                "committed_at": c.committed_at.isoformat() if c.committed_at else None,
            }
            for a, c in rows
        ],
    }
