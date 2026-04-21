"""
Scoring Engine V1 — calculates developer contribution scores.

Formula: Contribution Score = 15% Activity + 50% Quality + 35% Impact

Activity Score:
  - active_days, merged_pr_count, review_count

Quality Score:
  - work_item_coherence, meaningful_change_ratio, message_quality_ratio

Impact Score (V1 simplified):
  - weighted by lines changed on non-generated/non-lockfile code
  - bugfix weight (higher if commit messages mention fix/bug)
"""

import logging
import re
from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import Optional

from sqlalchemy.orm import Session
from sqlalchemy import func, cast, Date

from app.models.models import (
    Developer, Commit, CommitFile, PullRequest, Review,
    WorkItem, WorkItemCommit,
    ScoreSnapshot, ScoreBreakdown, AppConfig,
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
            return {**DEFAULT_WEIGHTS, **cfg.config_value}
        return DEFAULT_WEIGHTS.copy()

    # ────────────────────────────────────────────────────────────
    #  Main scoring
    # ────────────────────────────────────────────────────────────

    def calculate_score(
        self,
        developer_id: int,
        period_start: date,
        period_end: date,
    ) -> Optional[ScoreSnapshot]:
        """
        Calculate contribution score for a developer in a period.
        Returns the created ScoreSnapshot.
        """
        dev = self.db.query(Developer).get(developer_id)
        if not dev:
            logger.warning("Developer #%d not found", developer_id)
            return None

        if dev.is_bot:
            logger.info("Skipping bot: %s", dev.github_login)
            return None

        # Gather data for the period
        commits = (
            self.db.query(Commit)
            .filter(
                Commit.author_id == developer_id,
                Commit.committed_at >= datetime.combine(period_start, datetime.min.time()),
                Commit.committed_at <= datetime.combine(period_end, datetime.max.time()),
            )
            .all()
        )

        if not commits:
            logger.info("No commits for %s in period", dev.github_login)
            return None

        # Calculate sub-scores
        activity = self._calc_activity(developer_id, period_start, period_end, commits)
        quality = self._calc_quality(developer_id, commits)
        impact = self._calc_impact(developer_id, commits)

        # Weighted final
        w = self._weights
        final = (
            activity["score"] * w["activity_weight"]
            + quality["score"] * w["quality_weight"]
            + impact["score"] * w["impact_weight"]
        )

        # Confidence: based on data volume
        commit_count = len(commits)
        confidence = min(1.0, commit_count / 20)  # 20+ commits = full confidence

        # Positive / negative reasons
        positive_reasons = []
        negative_reasons = []

        if activity["active_days"] >= 10:
            positive_reasons.append(f"High activity: {activity['active_days']} active days")
        if quality["meaningful_ratio"] >= 0.8:
            positive_reasons.append(f"High-quality changes: {quality['meaningful_ratio']:.0%} meaningful")
        if impact["total_meaningful_lines"] > 500:
            positive_reasons.append(f"Significant impact: {impact['total_meaningful_lines']} meaningful lines")

        if activity["active_days"] < 3:
            negative_reasons.append(f"Low activity: only {activity['active_days']} active days")
        if quality["meaningful_ratio"] < 0.3:
            negative_reasons.append(f"Many trivial changes: {quality['meaningful_ratio']:.0%} meaningful")
        if quality["merge_ratio"] > 0.3:
            negative_reasons.append(f"High merge ratio: {quality['merge_ratio']:.0%}")

        # Delete old snapshot for same dev/period
        self.db.query(ScoreSnapshot).filter_by(
            developer_id=developer_id,
            period_start=period_start,
            period_end=period_end,
        ).delete(synchronize_session=False)

        snapshot = ScoreSnapshot(
            developer_id=developer_id,
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
            "Score for %s (%s to %s): %.2f (A=%.1f Q=%.1f I=%.1f, conf=%.2f)",
            dev.github_login, period_start, period_end,
            final, activity["score"], quality["score"], impact["score"], confidence,
        )
        return snapshot

    # ────────────────────────────────────────────────────────────
    #  Activity Score (0-100)
    # ────────────────────────────────────────────────────────────

    def _calc_activity(
        self, dev_id: int, start: date, end: date, commits: list[Commit]
    ) -> dict:
        """
        Activity = f(active_days, pr_count, review_count)
        """
        # Active days
        active_days = len(set(
            c.committed_at.date() for c in commits if c.committed_at
        ))

        # Merged PRs in period
        merged_prs = (
            self.db.query(func.count(PullRequest.id))
            .filter(
                PullRequest.author_id == dev_id,
                PullRequest.merged == True,
                PullRequest.merged_at >= datetime.combine(start, datetime.min.time()),
                PullRequest.merged_at <= datetime.combine(end, datetime.max.time()),
            )
            .scalar()
        ) or 0

        # Reviews given in period
        reviews_given = (
            self.db.query(func.count(Review.id))
            .filter(
                Review.reviewer_id == dev_id,
                Review.submitted_at >= datetime.combine(start, datetime.min.time()),
                Review.submitted_at <= datetime.combine(end, datetime.max.time()),
            )
            .scalar()
        ) or 0

        # Normalize: active_days → max 30 for full score
        days_score = min(100, (active_days / 20) * 100)
        pr_score = min(100, merged_prs * 15)  # each merged PR = 15 points
        review_score = min(100, reviews_given * 10)  # each review = 10 points

        score = days_score * 0.5 + pr_score * 0.3 + review_score * 0.2

        return {
            "score": min(100, score),
            "active_days": active_days,
            "merged_prs": merged_prs,
            "reviews_given": reviews_given,
            "commit_count": len(commits),
        }

    # ────────────────────────────────────────────────────────────
    #  Quality Score (0-100)
    # ────────────────────────────────────────────────────────────

    def _calc_quality(self, dev_id: int, commits: list[Commit]) -> dict:
        """
        Quality = f(coherence, meaningful_change_ratio, non-merge ratio)
        """
        total = len(commits)
        if total == 0:
            return {"score": 0, "meaningful_ratio": 0, "merge_ratio": 0, "work_item_count": 0}

        # Meaningful vs trivial commits
        meaningful = 0
        merge_count = 0
        for c in commits:
            if c.is_merge:
                merge_count += 1
                continue

            # Check if commit has meaningful files
            files = self.db.query(CommitFile).filter_by(commit_id=c.id).all()
            has_meaningful = any(
                not f.is_generated and not f.is_lockfile for f in files
            )
            if has_meaningful or (c.additions or 0) + (c.deletions or 0) > 0:
                meaningful += 1

        meaningful_ratio = meaningful / total if total > 0 else 0
        merge_ratio = merge_count / total if total > 0 else 0
        non_merge_ratio = 1 - merge_ratio

        # Work item coherence: fewer work items per commit = better coherence
        work_item_count = (
            self.db.query(func.count(func.distinct(WorkItemCommit.work_item_id)))
            .join(Commit, Commit.id == WorkItemCommit.commit_id)
            .filter(Commit.author_id == dev_id)
            .scalar()
        ) or 0

        # Coherence: ratio of commits to work items (higher = more grouped = better)
        non_merge_commits = total - merge_count
        if work_item_count > 0 and non_merge_commits > 0:
            coherence = min(1.0, non_merge_commits / (work_item_count * 1.5))
        else:
            coherence = 0.5  # no data, neutral

        # Message quality: rough check for descriptive messages
        good_messages = sum(
            1 for c in commits
            if c.message and len(c.message.split("\n")[0]) >= 10
            and not c.message.startswith("Merge")
        )
        message_quality = good_messages / total if total > 0 else 0

        score = (
            meaningful_ratio * 35
            + non_merge_ratio * 20
            + coherence * 25
            + message_quality * 20
        )

        return {
            "score": min(100, score),
            "meaningful_ratio": meaningful_ratio,
            "merge_ratio": merge_ratio,
            "coherence": coherence,
            "message_quality": message_quality,
            "work_item_count": work_item_count,
        }

    # ────────────────────────────────────────────────────────────
    #  Impact Score (0-100) — simplified V1
    # ────────────────────────────────────────────────────────────

    def _calc_impact(self, dev_id: int, commits: list[Commit]) -> dict:
        """
        Impact = weighted lines changed on meaningful files.
        Bonus for bugfix-related commits.
        """
        total_lines = 0
        meaningful_lines = 0
        bugfix_count = 0
        commit_ids = [c.id for c in commits]

        # Get all files for these commits
        if commit_ids:
            files = (
                self.db.query(CommitFile)
                .filter(CommitFile.commit_id.in_(commit_ids))
                .all()
            )
        else:
            files = []

        for f in files:
            lines = (f.additions or 0) + (f.deletions or 0)
            total_lines += lines
            if not f.is_generated and not f.is_lockfile:
                meaningful_lines += lines

        # Bugfix detection from commit messages
        bugfix_pattern = re.compile(
            r"\b(fix|bug|hotfix|patch|resolve|closes? #\d+)\b", re.IGNORECASE
        )
        for c in commits:
            if c.message and bugfix_pattern.search(c.message):
                bugfix_count += 1

        # Normalize meaningful lines: 2000 lines in period = 100
        lines_score = min(100, (meaningful_lines / 2000) * 100)

        # Bugfix bonus
        bugfix_bonus = min(20, bugfix_count * 5)

        # Meaningful-to-total ratio penalty
        if total_lines > 0:
            meaningful_ratio = meaningful_lines / total_lines
        else:
            meaningful_ratio = 1.0

        score = lines_score * 0.7 + bugfix_bonus + meaningful_ratio * 10

        return {
            "score": min(100, score),
            "total_lines": total_lines,
            "total_meaningful_lines": meaningful_lines,
            "meaningful_ratio": meaningful_ratio,
            "bugfix_count": bugfix_count,
        }

    # ────────────────────────────────────────────────────────────
    #  Batch scoring
    # ────────────────────────────────────────────────────────────

    def calculate_all_scores(
        self,
        period_start: date,
        period_end: date,
    ) -> list[ScoreSnapshot]:
        """Calculate scores for all active, non-bot developers."""
        devs = (
            self.db.query(Developer)
            .filter_by(is_active=True, is_bot=False)
            .all()
        )

        snapshots = []
        for dev in devs:
            snap = self.calculate_score(dev.id, period_start, period_end)
            if snap:
                snapshots.append(snap)

        logger.info("Calculated scores for %d developers", len(snapshots))
        return snapshots
