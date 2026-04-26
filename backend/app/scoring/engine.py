"""
Scoring Engine V2 — calculates developer contribution scores.

Formula: Contribution Score = 15% Activity + 50% Quality + 35% Impact

V2 enhancements:
  - Integrates AI analysis: message_alignment, complexity, change_type
  - Complexity-weighted impact scoring
  - Feature/bugfix/security bonuses from AI classification
"""

import logging
import re
from datetime import datetime, date
from decimal import Decimal
from typing import Optional

from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.models import (
    Developer, Commit, CommitFile, PullRequest, Review,
    WorkItem, WorkItemCommit, AICommitAnalysis,
    ScoreSnapshot, ScoreBreakdown, AppConfig, Repository,
)

logger = logging.getLogger(__name__)

# Default scoring weights
DEFAULT_WEIGHTS = {
    "activity_weight": 0.15,
    "quality_weight": 0.50,
    "impact_weight": 0.35,
}


class ScoringEngine:
    """Calculates contribution scores for developers."""

    def __init__(self, db: Session):
        self.db = db
        self._weights = self._load_weights()

    def _load_weights(self) -> dict:
        """Load scoring weights from app_configs."""
        cfg = (
            self.db.query(AppConfig)
            .filter_by(config_key="scoring_weights")
            .first()
        )
        if cfg and isinstance(cfg.config_value, dict):
            value = cfg.config_value
            return {
                "activity_weight": float(
                    value.get("activity_weight", value.get("activity", DEFAULT_WEIGHTS["activity_weight"]))
                ),
                "quality_weight": float(
                    value.get("quality_weight", value.get("quality", DEFAULT_WEIGHTS["quality_weight"]))
                ),
                "impact_weight": float(
                    value.get("impact_weight", value.get("impact", DEFAULT_WEIGHTS["impact_weight"]))
                ),
            }
        return DEFAULT_WEIGHTS.copy()

    @staticmethod
    def _period_bounds(period_start: date, period_end: date) -> tuple[datetime, datetime]:
        return (
            datetime.combine(period_start, datetime.min.time()),
            datetime.combine(period_end, datetime.max.time()),
        )

    # ────────────────────────────────────────────────────────────
    #  Main scoring
    # ────────────────────────────────────────────────────────────

    def calculate_score(
        self,
        developer_id: int,
        repo_id: int | None = None,
        period_start: date | None = None,
        period_end: date | None = None,
    ) -> Optional[ScoreSnapshot]:
        """
        Calculate contribution score for a developer in a period and optional repo.
        Returns the created ScoreSnapshot.
        """
        # Backward compatibility for old calls:
        # calculate_score(developer_id, period_start, period_end)
        if isinstance(repo_id, date) and isinstance(period_start, date) and period_end is None:
            period_end = period_start
            period_start = repo_id
            repo_id = None

        if period_start is None or period_end is None:
            raise ValueError("period_start and period_end are required")

        dev = self.db.get(Developer, developer_id)
        if not dev:
            logger.warning("Developer #%d not found", developer_id)
            return None

        if dev.is_bot:
            logger.info("Skipping bot: %s", dev.github_login)
            return None

        repo = None
        if repo_id is not None:
            repo = self.db.get(Repository, repo_id)
            if not repo:
                raise ValueError(f"Repository #{repo_id} not found")

        # Gather data for the period
        start_dt, end_dt = self._period_bounds(period_start, period_end)
        commit_query = self.db.query(Commit).filter(
            Commit.author_id == developer_id,
            Commit.committed_at >= start_dt,
            Commit.committed_at <= end_dt,
        )
        if repo_id is not None:
            commit_query = commit_query.filter(Commit.repo_id == repo_id)
        commits = commit_query.all()

        if not commits:
            self._delete_existing_snapshot(developer_id, repo_id, period_start, period_end)
            self.db.commit()
            logger.info(
                "No commits for %s in %s (%s to %s)",
                dev.github_login,
                repo.full_name if repo else "global scope",
                period_start,
                period_end,
            )
            return None

        # Gather AI analysis data for these commits
        commit_ids = [c.id for c in commits]
        ai_data = self._get_ai_data(commit_ids)

        # Calculate sub-scores
        activity = self._calc_activity(developer_id, repo_id, period_start, period_end, commits)
        quality = self._calc_quality(developer_id, repo_id, period_start, period_end, commits, ai_data)
        impact = self._calc_impact(developer_id, commits, ai_data)

        # Weighted final
        w = self._weights
        final = (
            activity["score"] * w["activity_weight"]
            + quality["score"] * w["quality_weight"]
            + impact["score"] * w["impact_weight"]
        )

        # Confidence: based on multiple repo-scoped data signals, not raw commits only.
        commit_count = len(commits)
        confidence = self._calc_confidence(activity, quality, ai_data)

        # Positive / negative reasons
        positive_reasons = []
        negative_reasons = []

        if activity["active_days"] >= 10:
            positive_reasons.append(f"High activity: {activity['active_days']} active days")
        if quality["meaningful_ratio"] >= 0.8:
            positive_reasons.append(f"High-quality changes: {quality['meaningful_ratio']:.0%} meaningful")
        if impact["total_meaningful_lines"] > 500:
            positive_reasons.append(f"Significant impact: {impact['total_meaningful_lines']} meaningful lines")
        if quality.get("avg_alignment", 0) >= 60:
            positive_reasons.append(f"Good commit messages: {quality['avg_alignment']:.0f}/100 alignment")
        if impact.get("feature_count", 0) >= 3:
            positive_reasons.append(f"Feature-rich: {impact['feature_count']} features delivered")

        if activity["active_days"] < 3:
            negative_reasons.append(f"Low activity: only {activity['active_days']} active days")
        if quality["meaningful_ratio"] < 0.3:
            negative_reasons.append(f"Many trivial changes: {quality['meaningful_ratio']:.0%} meaningful")
        if quality["merge_ratio"] > 0.3:
            negative_reasons.append(f"High merge ratio: {quality['merge_ratio']:.0%}")
        if quality.get("avg_alignment", 0) < 30 and quality.get("avg_alignment", 0) > 0:
            negative_reasons.append(f"Poor commit messages: {quality['avg_alignment']:.0f}/100 alignment")

        # Delete old snapshot for same developer/repo/period.
        self._delete_existing_snapshot(developer_id, repo_id, period_start, period_end)

        scope_label = repo.full_name if repo else "Toan he thong"

        snapshot = ScoreSnapshot(
            developer_id=developer_id,
            repo_id=repo_id,
            period_start=period_start,
            period_end=period_end,
            activity_score=Decimal(str(round(activity["score"], 2))),
            quality_score=Decimal(str(round(quality["score"], 2))),
            impact_score=Decimal(str(round(impact["score"], 2))),
            final_score=Decimal(str(round(final, 2))),
            confidence_score=Decimal(str(round(confidence, 2))),
            top_positive_reasons=positive_reasons[:5],
            top_negative_reasons=negative_reasons[:5],
            evidence_links=[
                f"Repo: {scope_label}",
                f"Commits: {commit_count}",
                f"Active days: {activity['active_days']}",
                f"Work items: {quality.get('work_item_count', 0)}",
            ],
        )
        self.db.add(snapshot)
        self.db.flush()

        # Score breakdowns
        breakdowns = [
            ("activity_score", activity["score"], w["activity_weight"], activity),
            ("quality_score", quality["score"], w["quality_weight"], quality),
            ("impact_score", impact["score"], w["impact_weight"], impact),
        ]
        for comp, raw, weight, details in breakdowns:
            bd = ScoreBreakdown(
                snapshot_id=snapshot.id,
                component=comp,
                raw_value=Decimal(str(round(raw, 4))),
                weight=Decimal(str(weight)),
                weighted_value=Decimal(str(round(raw * weight, 4))),
                details={k: v for k, v in details.items() if k != "score"},
            )
            self.db.add(bd)

        self.db.commit()
        logger.info(
            "Score for %s in %s (%s to %s): %.2f (A=%.1f Q=%.1f I=%.1f, conf=%.2f)",
            dev.github_login,
            repo.full_name if repo else "global scope",
            period_start,
            period_end,
            final, activity["score"], quality["score"], impact["score"], confidence,
        )
        return snapshot

    # ────────────────────────────────────────────────────────────
    #  Activity Score (0-100)
    # ────────────────────────────────────────────────────────────

    def _delete_existing_snapshot(
        self,
        developer_id: int,
        repo_id: int | None,
        period_start: date,
        period_end: date,
    ) -> None:
        query = self.db.query(ScoreSnapshot).filter(
            ScoreSnapshot.developer_id == developer_id,
            ScoreSnapshot.period_start == period_start,
            ScoreSnapshot.period_end == period_end,
        )
        if repo_id is None:
            query = query.filter(ScoreSnapshot.repo_id.is_(None))
        else:
            query = query.filter(ScoreSnapshot.repo_id == repo_id)
        query.delete(synchronize_session=False)

    def _count_work_items(
        self,
        dev_id: int,
        repo_id: int | None,
        start: date,
        end: date,
    ) -> int:
        start_dt, end_dt = self._period_bounds(start, end)
        query = (
            self.db.query(func.count(func.distinct(WorkItemCommit.work_item_id)))
            .join(Commit, Commit.id == WorkItemCommit.commit_id)
            .join(WorkItem, WorkItem.id == WorkItemCommit.work_item_id)
            .filter(
                Commit.author_id == dev_id,
                Commit.committed_at >= start_dt,
                Commit.committed_at <= end_dt,
            )
        )
        if repo_id is not None:
            query = query.filter(Commit.repo_id == repo_id)
        return query.scalar() or 0

    def _calc_activity(
        self,
        dev_id: int,
        repo_id: int | None,
        start: date,
        end: date,
        commits: list[Commit],
    ) -> dict:
        """
        Activity = f(active_days, pr_count, review_count)
        """
        # Active days
        active_days = len(set(
            c.committed_at.date() for c in commits if c.committed_at
        ))
        start_dt, end_dt = self._period_bounds(start, end)

        # Merged PRs in period
        pr_query = self.db.query(func.count(PullRequest.id)).filter(
            PullRequest.author_id == dev_id,
            PullRequest.merged == True,
            PullRequest.merged_at >= start_dt,
            PullRequest.merged_at <= end_dt,
        )
        if repo_id is not None:
            pr_query = pr_query.filter(PullRequest.repo_id == repo_id)
        merged_prs = pr_query.scalar() or 0

        # Reviews given in period
        review_query = (
            self.db.query(func.count(Review.id))
            .join(PullRequest, PullRequest.id == Review.pull_request_id)
            .filter(
                Review.reviewer_id == dev_id,
                Review.submitted_at >= start_dt,
                Review.submitted_at <= end_dt,
            )
        )
        if repo_id is not None:
            review_query = review_query.filter(PullRequest.repo_id == repo_id)
        reviews_given = review_query.scalar() or 0

        work_item_count = self._count_work_items(dev_id, repo_id, start, end)

        # Normalize: active_days → max 30 for full score
        days_score = min(100, (active_days / 20) * 100)
        pr_score = min(100, merged_prs * 15)  # each merged PR = 15 points
        review_score = min(100, reviews_given * 10)  # each review = 10 points
        work_item_score = min(100, work_item_count * 20)

        score = (
            days_score * 0.4
            + pr_score * 0.25
            + review_score * 0.15
            + work_item_score * 0.2
        )

        return {
            "score": min(100, score),
            "active_days": active_days,
            "merged_prs": merged_prs,
            "reviews_given": reviews_given,
            "work_item_count": work_item_count,
            "commit_count": len(commits),
        }

    # ────────────────────────────────────────────────────────────
    #  Quality Score (0-100)
    # ────────────────────────────────────────────────────────────

    def _calc_quality(
        self,
        dev_id: int,
        repo_id: int | None,
        start: date,
        end: date,
        commits: list[Commit],
        ai_data: dict = None,
    ) -> dict:
        """
        Quality V2 = f(coherence, meaningful_ratio, non-merge, message_alignment, ai_quality)
        """
        ai_data = ai_data or {}
        total = len(commits)
        if total == 0:
            return {
                "score": 0,
                "meaningful_ratio": 0,
                "merge_ratio": 0,
                "work_item_count": 0,
                "avg_alignment": 0,
                "meaningful_count": 0,
            }

        # Meaningful vs trivial commits
        meaningful = 0
        merge_count = 0
        for c in commits:
            if c.is_merge:
                merge_count += 1
                continue
            files = self.db.query(CommitFile).filter_by(commit_id=c.id).all()
            has_meaningful = any(not f.is_generated and not f.is_lockfile for f in files)
            if has_meaningful or (c.additions or 0) + (c.deletions or 0) > 0:
                meaningful += 1

        meaningful_ratio = meaningful / total if total > 0 else 0
        merge_ratio = merge_count / total if total > 0 else 0
        non_merge_ratio = 1 - merge_ratio

        # Work item coherence
        work_item_count = self._count_work_items(dev_id, repo_id, start, end)

        non_merge_commits = total - merge_count
        if work_item_count > 0 and non_merge_commits > 0:
            coherence = min(1.0, non_merge_commits / (work_item_count * 1.5))
        else:
            coherence = 0.5

        # Message quality: V1 heuristic
        good_messages = sum(
            1 for c in commits
            if c.message and len(c.message.split("\n")[0]) >= 10
            and not c.message.startswith("Merge")
        )
        message_quality = good_messages / total if total > 0 else 0

        # V2: AI message alignment (average from ai_commit_analysis)
        ai_alignments = [a.get("message_alignment_score", 0) for a in ai_data.values() if a.get("message_alignment_score")]
        avg_alignment = sum(ai_alignments) / len(ai_alignments) if ai_alignments else 0
        alignment_factor = avg_alignment / 100 if avg_alignment > 0 else message_quality

        score = (
            meaningful_ratio * 25
            + non_merge_ratio * 15
            + coherence * 25
            + alignment_factor * 20
            + message_quality * 15
        )

        return {
            "score": min(100, score),
            "meaningful_ratio": meaningful_ratio,
            "merge_ratio": merge_ratio,
            "coherence": coherence,
            "message_quality": message_quality,
            "avg_alignment": avg_alignment,
            "work_item_count": work_item_count,
            "meaningful_count": meaningful,
        }

    def _calc_confidence(self, activity: dict, quality: dict, ai_data: dict) -> float:
        """Estimate confidence from repo-scoped data volume and analysis quality."""
        high_conf_ai = sum(
            1
            for item in ai_data.values()
            if float(item.get("confidence") or 0) >= 0.7
        )
        weighted_volume = (
            activity.get("active_days", 0) * 0.35
            + quality.get("meaningful_count", 0) * 0.6
            + activity.get("merged_prs", 0) * 1.5
            + activity.get("reviews_given", 0) * 0.8
            + quality.get("work_item_count", 0) * 2.0
            + high_conf_ai * 0.4
        )
        return min(1.0, weighted_volume / 20)

    # ────────────────────────────────────────────────────────────
    #  Impact Score (0-100) — V2 with AI data
    # ────────────────────────────────────────────────────────────

    def _calc_impact(self, dev_id: int, commits: list[Commit], ai_data: dict = None) -> dict:
        """
        Impact V2 = complexity-weighted lines + change_type bonuses from AI.
        """
        ai_data = ai_data or {}
        total_lines = 0
        meaningful_lines = 0
        bugfix_count = 0
        feature_count = 0
        security_count = 0
        commit_ids = [c.id for c in commits]

        if commit_ids:
            files = self.db.query(CommitFile).filter(CommitFile.commit_id.in_(commit_ids)).all()
        else:
            files = []

        for f in files:
            lines = (f.additions or 0) + (f.deletions or 0)
            total_lines += lines
            if not f.is_generated and not f.is_lockfile:
                meaningful_lines += lines

        # V2: Use AI change_type classification
        for cid, ai in ai_data.items():
            ct = ai.get("change_type", "")
            if ct == "bugfix":
                bugfix_count += 1
            elif ct == "feature":
                feature_count += 1
            elif ct == "security":
                security_count += 1

        # Fallback: detect bugfix from messages if no AI data
        if not ai_data:
            bugfix_pattern = re.compile(r"\b(fix|bug|hotfix|patch|resolve|closes? #\d+)\b", re.IGNORECASE)
            for c in commits:
                if c.message and bugfix_pattern.search(c.message):
                    bugfix_count += 1

        # V2: Complexity-weighted lines
        avg_complexity = 0
        if ai_data:
            complexities = [a.get("complexity_score", 30) for a in ai_data.values()]
            avg_complexity = sum(complexities) / len(complexities) if complexities else 30
            # Higher complexity = more impactful work
            complexity_multiplier = 0.7 + (avg_complexity / 100) * 0.6  # 0.7-1.3x
        else:
            complexity_multiplier = 1.0

        lines_score = min(100, (meaningful_lines / 2000) * 100) * complexity_multiplier

        # Bonuses
        bugfix_bonus = min(15, bugfix_count * 5)
        feature_bonus = min(15, feature_count * 3)
        security_bonus = min(10, security_count * 10)

        if total_lines > 0:
            meaningful_ratio = meaningful_lines / total_lines
        else:
            meaningful_ratio = 1.0

        score = lines_score * 0.6 + bugfix_bonus + feature_bonus + security_bonus + meaningful_ratio * 10

        return {
            "score": min(100, score),
            "total_lines": total_lines,
            "total_meaningful_lines": meaningful_lines,
            "meaningful_ratio": meaningful_ratio,
            "bugfix_count": bugfix_count,
            "feature_count": feature_count,
            "security_count": security_count,
            "avg_complexity": round(avg_complexity, 1),
        }

    # ────────────────────────────────────────────────────────────
    #  AI Data Helper
    # ────────────────────────────────────────────────────────────

    def _get_ai_data(self, commit_ids: list[int]) -> dict:
        """Load AI analysis results for commits, keyed by commit_id."""
        if not commit_ids:
            return {}
        analyses = (
            self.db.query(AICommitAnalysis)
            .filter(
                AICommitAnalysis.target_type == "commit",
                AICommitAnalysis.target_id.in_(commit_ids),
            )
            .all()
        )
        return {
            a.target_id: {
                "change_type": a.change_type,
                "complexity_score": a.complexity_score,
                "risk_score": a.risk_score,
                "message_alignment_score": a.message_alignment_score,
                "test_presence": a.test_presence,
                "confidence": float(a.confidence) if a.confidence else 0,
            }
            for a in analyses
        }

    # ────────────────────────────────────────────────────────────
    #  Batch scoring
    # ────────────────────────────────────────────────────────────

    def calculate_all_scores(
        self,
        repo_id: int | None = None,
        period_start: date | None = None,
        period_end: date | None = None,
    ) -> list[ScoreSnapshot]:
        """Calculate scores for active, non-bot developers in a repo or global scope."""
        # Backward compatibility for old calls:
        # calculate_all_scores(period_start, period_end)
        if isinstance(repo_id, date) and isinstance(period_start, date) and period_end is None:
            period_end = period_start
            period_start = repo_id
            repo_id = None

        if period_start is None or period_end is None:
            raise ValueError("period_start and period_end are required")

        repo = None
        if repo_id is not None:
            repo = self.db.get(Repository, repo_id)
            if not repo:
                raise ValueError(f"Repository #{repo_id} not found")

        start_dt, end_dt = self._period_bounds(period_start, period_end)
        dev_query = (
            self.db.query(Developer)
            .join(Commit, Commit.author_id == Developer.id)
            .filter(
                Developer.is_active == True,
                Developer.is_bot == False,
                Commit.committed_at >= start_dt,
                Commit.committed_at <= end_dt,
            )
            .distinct()
        )
        if repo_id is not None:
            dev_query = dev_query.filter(Commit.repo_id == repo_id)
        devs = dev_query.all()

        snapshots = []
        for dev in devs:
            snap = self.calculate_score(dev.id, repo_id, period_start, period_end)
            if snap:
                snapshots.append(snap)

        logger.info(
            "Calculated scores for %d developers in %s",
            len(snapshots),
            repo.full_name if repo else "global scope",
        )
        return snapshots
