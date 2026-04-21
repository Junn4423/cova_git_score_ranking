"""
AI Analysis Service — runs the analyzer on commits and saves results to DB.
"""

import logging
from decimal import Decimal
from typing import Optional

from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.models import (
    Commit, CommitFile, AICommitAnalysis, Repository,
)
from app.ai.analyzer import analyze_commit, AnalysisResult

logger = logging.getLogger(__name__)

MODEL_VERSION = "rule-based-v1"
PROMPT_VERSION = "n/a"
SCHEMA_VERSION = "1.0"


class AnalysisService:
    """Runs AI analysis on commits and stores results."""

    def __init__(self, db: Session):
        self.db = db

    def analyze_repo(self, repo_id: int, force: bool = False) -> dict:
        """
        Analyze all commits in a repository.
        If force=False, skip already analyzed commits.
        Returns summary stats.
        """
        repo = self.db.query(Repository).get(repo_id)
        if not repo:
            raise ValueError(f"Repository #{repo_id} not found")

        commits = (
            self.db.query(Commit)
            .filter_by(repo_id=repo_id)
            .order_by(Commit.committed_at.asc())
            .all()
        )

        analyzed = 0
        skipped = 0
        errors = 0

        for commit in commits:
            try:
                # Check if already analyzed
                if not force:
                    existing = (
                        self.db.query(AICommitAnalysis)
                        .filter_by(target_type="commit", target_id=commit.id)
                        .first()
                    )
                    if existing:
                        skipped += 1
                        continue

                result = self._analyze_single_commit(commit)
                if result:
                    analyzed += 1
                else:
                    skipped += 1
            except Exception as e:
                logger.warning("Failed to analyze commit #%d: %s", commit.id, e)
                errors += 1

        self.db.commit()

        logger.info(
            "Analyzed repo %s: %d analyzed, %d skipped, %d errors",
            repo.full_name, analyzed, skipped, errors,
        )

        return {
            "repo": repo.full_name,
            "total_commits": len(commits),
            "analyzed": analyzed,
            "skipped": skipped,
            "errors": errors,
        }

    def analyze_single(self, commit_id: int, force: bool = False) -> Optional[dict]:
        """Analyze a single commit."""
        commit = self.db.query(Commit).get(commit_id)
        if not commit:
            raise ValueError(f"Commit #{commit_id} not found")

        if not force:
            existing = (
                self.db.query(AICommitAnalysis)
                .filter_by(target_type="commit", target_id=commit.id)
                .first()
            )
            if existing:
                return self._analysis_to_dict(existing)

        result = self._analyze_single_commit(commit)
        self.db.commit()

        if result:
            return self._result_to_dict(result, commit)
        return None

    def _analyze_single_commit(self, commit: Commit) -> Optional[AnalysisResult]:
        """Run analysis on a single commit and save to DB."""
        # Get commit files
        files = self.db.query(CommitFile).filter_by(commit_id=commit.id).all()
        file_dicts = [
            {
                "filename": f.filename,
                "status": f.status,
                "additions": f.additions or 0,
                "deletions": f.deletions or 0,
                "patch": f.patch,
                "is_generated": f.is_generated,
                "is_lockfile": f.is_lockfile,
            }
            for f in files
        ]

        # Run analyzer
        result = analyze_commit(
            message=commit.message or "",
            files=file_dicts,
            additions=commit.additions or 0,
            deletions=commit.deletions or 0,
            is_merge=commit.is_merge or False,
        )

        # Delete old analysis if exists
        self.db.query(AICommitAnalysis).filter_by(
            target_type="commit", target_id=commit.id
        ).delete(synchronize_session=False)

        # Save to DB
        analysis = AICommitAnalysis(
            target_type="commit",
            target_id=commit.id,
            change_type=result.change_type,
            summary=result.summary,
            complexity_score=result.complexity_score,
            risk_score=result.risk_score,
            message_alignment_score=result.message_alignment_score,
            test_presence=result.test_presence,
            confidence=Decimal(str(result.confidence)),
            notes=result.notes,
            model_version=MODEL_VERSION,
            prompt_version=PROMPT_VERSION,
            schema_version=SCHEMA_VERSION,
            raw_response=None,
        )
        self.db.add(analysis)

        return result

    def get_stats(self) -> dict:
        """Return analysis statistics."""
        total = self.db.query(func.count(AICommitAnalysis.id)).scalar() or 0
        by_type = (
            self.db.query(
                AICommitAnalysis.change_type,
                func.count(AICommitAnalysis.id),
            )
            .group_by(AICommitAnalysis.change_type)
            .all()
        )
        avg_complexity = (
            self.db.query(func.avg(AICommitAnalysis.complexity_score)).scalar()
        )
        avg_risk = (
            self.db.query(func.avg(AICommitAnalysis.risk_score)).scalar()
        )
        avg_alignment = (
            self.db.query(func.avg(AICommitAnalysis.message_alignment_score)).scalar()
        )
        avg_confidence = (
            self.db.query(func.avg(AICommitAnalysis.confidence)).scalar()
        )

        return {
            "total_analyzed": total,
            "by_change_type": {t: c for t, c in by_type},
            "avg_complexity": round(float(avg_complexity), 1) if avg_complexity else 0,
            "avg_risk": round(float(avg_risk), 1) if avg_risk else 0,
            "avg_alignment": round(float(avg_alignment), 1) if avg_alignment else 0,
            "avg_confidence": round(float(avg_confidence), 2) if avg_confidence else 0,
        }

    def _analysis_to_dict(self, a: AICommitAnalysis) -> dict:
        return {
            "id": a.id,
            "target_type": a.target_type,
            "target_id": a.target_id,
            "change_type": a.change_type,
            "summary": a.summary,
            "complexity_score": a.complexity_score,
            "risk_score": a.risk_score,
            "message_alignment_score": a.message_alignment_score,
            "test_presence": a.test_presence,
            "confidence": float(a.confidence) if a.confidence else 0,
            "notes": a.notes,
            "model_version": a.model_version,
            "created_at": a.created_at.isoformat() if a.created_at else None,
        }

    def _result_to_dict(self, result: AnalysisResult, commit: Commit) -> dict:
        return {
            "target_type": "commit",
            "target_id": commit.id,
            "sha": commit.sha,
            "change_type": result.change_type,
            "summary": result.summary,
            "complexity_score": result.complexity_score,
            "risk_score": result.risk_score,
            "message_alignment_score": result.message_alignment_score,
            "test_presence": result.test_presence,
            "confidence": result.confidence,
            "notes": result.notes,
        }
