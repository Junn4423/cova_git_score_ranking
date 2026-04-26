"""
Evaluation service: orchestrates repo sync, grouping, analysis, scoring, and report data.
"""

from __future__ import annotations

import re
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.ai.service import AnalysisService
from app.core.config import settings
from app.models.models import (
    Commit,
    EvaluationResult,
    EvaluationRun,
    PullRequest,
    Repository,
    ScoreSnapshot,
    User,
    WorkItem,
)
from app.scoring.engine import ScoringEngine
from app.services.grouping import GroupingService
from app.services.ingestion import IngestionService


class EvaluationService:
    def __init__(self, db: Session):
        self.db = db

    def create_and_run(
        self,
        *,
        repo_url: str,
        period_days: int = 90,
        max_commit_pages: int = 5,
        max_pr_pages: int = 5,
        run_analysis: bool = True,
        force_resync: bool = False,
        requested_by: User | None = None,
    ) -> EvaluationRun:
        full_name = self.parse_repo_url(repo_url)
        period_end = date.today()
        period_start = period_end - timedelta(days=period_days)

        ingestion = IngestionService(self.db)
        repo = self.db.query(Repository).filter_by(full_name=full_name).first()
        if not repo or force_resync:
            repo = ingestion.sync_single_repo(full_name)

        run = EvaluationRun(
            repo_id=repo.id,
            requested_by_user_id=requested_by.id if requested_by else None,
            status="running",
            current_step="sync_repo",
            period_start=period_start,
            period_end=period_end,
            input_repo_url=repo_url,
            access_mode="server_token" if settings.GITHUB_TOKEN else "public",
        )
        self.db.add(run)
        self.db.commit()
        self.db.refresh(run)

        try:
            self._set_step(run, "sync_repo")
            run.sync_started_at = datetime.utcnow()
            self.db.commit()
            ingestion.full_sync_repo(
                full_name=full_name,
                since=period_start.isoformat(),
                max_commit_pages=max_commit_pages,
                max_pr_pages=max_pr_pages,
                fetch_files=True,
            )
            repo = self.db.query(Repository).filter_by(full_name=full_name).first()
            run.repo_id = repo.id
            run.sync_completed_at = datetime.utcnow()
            self.db.commit()

            self._set_step(run, "build_work_items")
            grouping = GroupingService(self.db)
            grouping.clear_work_items_for_repo(repo.id)
            grouping.build_work_items_for_repo(repo.id)
            run.grouping_completed_at = datetime.utcnow()
            self.db.commit()

            if run_analysis:
                self._set_step(run, "run_analysis")
                AnalysisService(self.db).analyze_repo(repo.id, force=force_resync)
                run.analysis_completed_at = datetime.utcnow()
                self.db.commit()

            self._set_step(run, "calculate_scores")
            snapshots = ScoringEngine(self.db).calculate_all_scores(
                repo.id,
                period_start,
                period_end,
            )
            run.scoring_completed_at = datetime.utcnow()
            self.db.commit()

            self._set_step(run, "generate_report")
            self._persist_results(run, repo, snapshots)
            run.report_completed_at = datetime.utcnow()
            run.status = "done"
            run.current_step = "done"
            self.db.commit()
            self.db.refresh(run)
            return run
        except Exception as exc:
            run.status = "failed"
            run.error_message = str(exc)
            self.db.commit()
            raise

    @staticmethod
    def parse_repo_url(repo_url: str) -> str:
        value = repo_url.strip()
        patterns = [
            r"^https://github\.com/([^/\s]+)/([^/\s]+?)(?:\.git)?/?$",
            r"^git@github\.com:([^/\s]+)/([^/\s]+?)(?:\.git)?$",
            r"^([^/\s]+)/([^/\s]+)$",
        ]
        for pattern in patterns:
            match = re.match(pattern, value)
            if match:
                owner, repo = match.group(1), match.group(2)
                return f"{owner}/{repo.removesuffix('.git')}"
        raise ValueError("Invalid GitHub repository URL")

    def get_run(self, evaluation_id: int) -> EvaluationRun | None:
        return self.db.get(EvaluationRun, evaluation_id)

    def list_runs(self, limit: int = 50) -> list[EvaluationRun]:
        return (
            self.db.query(EvaluationRun)
            .order_by(EvaluationRun.created_at.desc())
            .limit(limit)
            .all()
        )

    def get_results(self, evaluation_id: int) -> list[EvaluationResult]:
        return (
            self.db.query(EvaluationResult)
            .filter_by(evaluation_run_id=evaluation_id)
            .order_by(EvaluationResult.rank_no.asc())
            .all()
        )

    def get_report(self, evaluation_id: int) -> dict[str, Any]:
        run = self.get_run(evaluation_id)
        if not run:
            raise ValueError("Evaluation run not found")

        repo = run.repository
        results = self.get_results(evaluation_id)
        commit_count = (
            self.db.query(func.count(Commit.id))
            .filter(
                Commit.repo_id == run.repo_id,
                Commit.committed_at >= datetime.combine(run.period_start, datetime.min.time()),
                Commit.committed_at <= datetime.combine(run.period_end, datetime.max.time()),
            )
            .scalar()
            or 0
        )
        pr_count = self.db.query(func.count(PullRequest.id)).filter_by(repo_id=run.repo_id).scalar() or 0
        work_item_count = self.db.query(func.count(WorkItem.id)).filter_by(repo_id=run.repo_id).scalar() or 0

        return {
            "evaluation": self.serialize_run(run),
            "repo": {
                "id": repo.id,
                "full_name": repo.full_name,
                "name": repo.name,
            },
            "summary": {
                "period_start": run.period_start.isoformat(),
                "period_end": run.period_end.isoformat(),
                "developer_count": len(results),
                "commit_count": commit_count,
                "pull_request_count": pr_count,
                "work_item_count": work_item_count,
            },
            "ranking": [self.serialize_result(result) for result in results],
        }

    def _set_step(self, run: EvaluationRun, step: str) -> None:
        run.current_step = step
        run.status = "running"
        self.db.commit()

    def _persist_results(
        self,
        run: EvaluationRun,
        repo: Repository,
        snapshots: list[ScoreSnapshot],
    ) -> None:
        self.db.query(EvaluationResult).filter_by(evaluation_run_id=run.id).delete(
            synchronize_session=False
        )
        ordered = sorted(
            snapshots,
            key=lambda item: float(item.final_score or 0),
            reverse=True,
        )
        for index, snapshot in enumerate(ordered, start=1):
            developer = snapshot.developer
            positives = snapshot.top_positive_reasons or []
            negatives = snapshot.top_negative_reasons or []
            evidence_links = snapshot.evidence_links or []
            result = EvaluationResult(
                evaluation_run_id=run.id,
                developer_id=snapshot.developer_id,
                repo_id=repo.id,
                rank_no=index,
                final_score=snapshot.final_score or Decimal("0"),
                activity_score=snapshot.activity_score,
                quality_score=snapshot.quality_score,
                impact_score=snapshot.impact_score,
                confidence_score=snapshot.confidence_score,
                summary_vi=(
                    f"{developer.github_login if developer else 'Developer'} dat "
                    f"{float(snapshot.final_score or 0):.2f} diem trong repo {repo.full_name} "
                    f"cho giai doan {run.period_start} den {run.period_end}."
                ),
                strengths=positives[:5] or ["Co dong gop duoc ghi nhan trong repo nay."],
                weaknesses=negatives[:5] or ["Chua co diem yeu ro rang tu du lieu hien co."],
                recommendations=[
                    "Tiep tuc tach cong viec thanh work item ro rang.",
                    "Bo sung test va PR review cho thay doi co rui ro cao.",
                ],
                evidence=[
                    {
                        "type": "score_snapshot",
                        "snapshot_id": snapshot.id,
                        "details": evidence_links,
                    }
                ],
            )
            self.db.add(result)
        self.db.commit()

    @staticmethod
    def serialize_run(run: EvaluationRun) -> dict[str, Any]:
        return {
            "id": run.id,
            "repo_id": run.repo_id,
            "repo_full_name": run.repository.full_name if run.repository else None,
            "requested_by_user_id": run.requested_by_user_id,
            "status": run.status,
            "current_step": run.current_step,
            "period_start": run.period_start.isoformat() if run.period_start else None,
            "period_end": run.period_end.isoformat() if run.period_end else None,
            "input_repo_url": run.input_repo_url,
            "access_mode": run.access_mode,
            "sync_started_at": run.sync_started_at.isoformat() if run.sync_started_at else None,
            "sync_completed_at": run.sync_completed_at.isoformat() if run.sync_completed_at else None,
            "grouping_completed_at": run.grouping_completed_at.isoformat() if run.grouping_completed_at else None,
            "analysis_completed_at": run.analysis_completed_at.isoformat() if run.analysis_completed_at else None,
            "scoring_completed_at": run.scoring_completed_at.isoformat() if run.scoring_completed_at else None,
            "report_completed_at": run.report_completed_at.isoformat() if run.report_completed_at else None,
            "error_message": run.error_message,
            "created_at": run.created_at.isoformat() if run.created_at else None,
            "updated_at": run.updated_at.isoformat() if run.updated_at else None,
        }

    @staticmethod
    def serialize_result(result: EvaluationResult) -> dict[str, Any]:
        developer = result.developer
        return {
            "id": result.id,
            "evaluation_run_id": result.evaluation_run_id,
            "developer_id": result.developer_id,
            "github_login": developer.github_login if developer else None,
            "display_name": developer.display_name if developer else None,
            "avatar_url": developer.avatar_url if developer else None,
            "repo_id": result.repo_id,
            "rank_no": result.rank_no,
            "final_score": float(result.final_score or 0),
            "activity_score": float(result.activity_score or 0),
            "quality_score": float(result.quality_score or 0),
            "impact_score": float(result.impact_score or 0),
            "confidence_score": float(result.confidence_score or 0),
            "summary_vi": result.summary_vi,
            "strengths": result.strengths or [],
            "weaknesses": result.weaknesses or [],
            "recommendations": result.recommendations or [],
            "evidence": result.evidence or [],
        }
