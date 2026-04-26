"""
Evaluation API endpoints.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user, require_roles
from app.models.models import User
from app.services.audit import log_audit
from app.services.evaluation_service import EvaluationService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/evaluations", tags=["Evaluations"])


class CreateEvaluationRequest(BaseModel):
    repo_url: str = Field(min_length=3, max_length=500)
    period_days: int = Field(default=30, ge=1, le=365)
    max_commit_pages: int = Field(default=1, ge=1, le=10)
    max_pr_pages: int = Field(default=1, ge=0, le=10)
    fetch_files: bool = False
    run_analysis: bool = True
    force_resync: bool = False


@router.post("")
def create_evaluation(
    req: CreateEvaluationRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "lead")),
):
    service = EvaluationService(db)
    try:
        run = service.create_and_run(
            repo_url=req.repo_url,
            period_days=req.period_days,
            max_commit_pages=req.max_commit_pages,
            max_pr_pages=req.max_pr_pages,
            fetch_files=req.fetch_files,
            run_analysis=req.run_analysis,
            force_resync=req.force_resync,
            requested_by=current_user,
        )
        log_audit(
            db,
            actor_id=current_user.id,
            action="evaluation.create",
            target_type="evaluation_run",
            target_id=run.id,
            details=req.model_dump(),
            ip_address=request.client.host if request.client else None,
        )
        db.commit()
        return {
            "evaluation_run_id": run.id,
            "repo_id": run.repo_id,
            "status": run.status,
            "current_step": run.current_step,
            "evaluation": service.serialize_run(run),
        }
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Evaluation failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Evaluation failed unexpectedly. Check backend logs for details.",
        ) from exc


@router.get("")
def list_evaluations(
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = EvaluationService(db)
    return [service.serialize_run(run) for run in service.list_runs(limit=limit)]


@router.get("/{evaluation_id}")
def get_evaluation(
    evaluation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = EvaluationService(db)
    run = service.get_run(evaluation_id)
    if not run:
        raise HTTPException(status_code=404, detail="Evaluation run not found")
    return service.serialize_run(run)


@router.get("/{evaluation_id}/results")
def get_evaluation_results(
    evaluation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = EvaluationService(db)
    if not service.get_run(evaluation_id):
        raise HTTPException(status_code=404, detail="Evaluation run not found")
    return [service.serialize_result(result) for result in service.get_results(evaluation_id)]


@router.get("/{evaluation_id}/report")
def get_evaluation_report(
    evaluation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = EvaluationService(db)
    try:
        return service.get_report(evaluation_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
