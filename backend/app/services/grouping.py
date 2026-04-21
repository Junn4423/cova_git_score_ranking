"""
Work-item grouping service — groups commits into logical work items.

Strategy (V1):
  1. PR-based:   commits already linked to a PR → 1 work item per PR
  2. Time-based: orphan commits by same author within a configurable
                 time window (default 8 hours) → 1 work item
  3. Lone:       any remaining commit → standalone work item

Also computes aggregated stats for each work item.
"""

import logging
from datetime import datetime, timedelta
from typing import Optional
from collections import defaultdict

from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.models import (
    Commit, CommitFile, PullRequest, PullRequestCommit,
    WorkItem, WorkItemCommit, Repository, Developer, AppConfig,
)

logger = logging.getLogger(__name__)

# Default grouping window in hours
DEFAULT_TIME_WINDOW_HOURS = 8


class GroupingService:
    """Groups commits into WorkItems for fairer scoring."""

    def __init__(self, db: Session):
        self.db = db
        self._time_window_hours = self._load_time_window()

    # ────────────────────────────────────────────────────────────
    #  Configuration
    # ────────────────────────────────────────────────────────────

    def _load_time_window(self) -> int:
        """Load grouping time window from app_configs."""
        cfg = (
            self.db.query(AppConfig)
            .filter_by(config_key="grouping_time_window_hours")
            .first()
        )
        if cfg and cfg.config_value:
            try:
                return int(cfg.config_value)
            except (TypeError, ValueError):
                pass
        return DEFAULT_TIME_WINDOW_HOURS

    # ────────────────────────────────────────────────────────────
    #  Main entry point
    # ────────────────────────────────────────────────────────────

    def build_work_items_for_repo(self, repo_id: int) -> dict:
        """
        Build work items for all commits in a repo.
        Returns summary stats.
        """
        repo = self.db.query(Repository).get(repo_id)
        if not repo:
            raise ValueError(f"Repository #{repo_id} not found")

        # Gather all commits for this repo
        all_commits = (
            self.db.query(Commit)
            .filter_by(repo_id=repo_id)
            .order_by(Commit.committed_at.asc())
            .all()
        )

        if not all_commits:
            return {
                "repo": repo.full_name,
                "total_commits": 0,
                "work_items_created": 0,
                "pr_based": 0,
                "time_based": 0,
                "lone": 0,
            }

        # Track which commits are already grouped
        grouped_commit_ids: set[int] = set()

        # Phase 1: PR-based grouping
        pr_items = self._group_by_pr(repo_id, grouped_commit_ids)

        # Phase 2: Time-window grouping for orphan commits
        time_items = self._group_by_time_window(
            repo_id, all_commits, grouped_commit_ids
        )

        # Phase 3: Lone commits (anything left)
        lone_items = self._group_lone_commits(
            repo_id, all_commits, grouped_commit_ids
        )

        self.db.commit()

        total_created = len(pr_items) + len(time_items) + len(lone_items)
        logger.info(
            "Built %d work items for %s (PR=%d, time=%d, lone=%d)",
            total_created, repo.full_name,
            len(pr_items), len(time_items), len(lone_items),
        )

        return {
            "repo": repo.full_name,
            "total_commits": len(all_commits),
            "work_items_created": total_created,
            "pr_based": len(pr_items),
            "time_based": len(time_items),
            "lone": len(lone_items),
        }

    # ────────────────────────────────────────────────────────────
    #  Phase 1: PR-based grouping
    # ────────────────────────────────────────────────────────────

    def _group_by_pr(
        self, repo_id: int, grouped_commit_ids: set[int]
    ) -> list[WorkItem]:
        """Create one WorkItem per PR that has linked commits."""
        prs = (
            self.db.query(PullRequest)
            .filter_by(repo_id=repo_id)
            .all()
        )

        work_items = []
        for pr in prs:
            # Get commits linked to this PR
            pr_commit_links = (
                self.db.query(PullRequestCommit)
                .filter_by(pull_request_id=pr.id)
                .all()
            )
            commit_ids = [pc.commit_id for pc in pr_commit_links]
            if not commit_ids:
                continue

            commits = (
                self.db.query(Commit)
                .filter(Commit.id.in_(commit_ids))
                .order_by(Commit.committed_at.asc())
                .all()
            )
            if not commits:
                continue

            # Determine author (PR author or most frequent commit author)
            author_id = pr.author_id or commits[0].author_id

            # Check if work item already exists for this PR
            existing = (
                self.db.query(WorkItem)
                .filter_by(repo_id=repo_id, pull_request_id=pr.id)
                .first()
            )
            if existing:
                # Update existing
                self._update_work_item(existing, commits)
                for c in commits:
                    grouped_commit_ids.add(c.id)
                work_items.append(existing)
                continue

            wi = self._create_work_item(
                developer_id=author_id,
                repo_id=repo_id,
                pull_request_id=pr.id,
                title=pr.title or f"PR #{pr.github_pr_number}",
                grouping_method="pr",
                commits=commits,
            )
            work_items.append(wi)
            for c in commits:
                grouped_commit_ids.add(c.id)

        return work_items

    # ────────────────────────────────────────────────────────────
    #  Phase 2: Time-window grouping
    # ────────────────────────────────────────────────────────────

    def _group_by_time_window(
        self,
        repo_id: int,
        all_commits: list[Commit],
        grouped_commit_ids: set[int],
    ) -> list[WorkItem]:
        """
        Group orphan commits by same author within a time window.
        Also considers branch overlap.
        """
        window = timedelta(hours=self._time_window_hours)

        # Filter to ungrouped commits with an author
        orphan_commits = [
            c for c in all_commits
            if c.id not in grouped_commit_ids
            and c.author_id is not None
            and c.committed_at is not None
        ]

        if not orphan_commits:
            return []

        # Group by author
        by_author: dict[int, list[Commit]] = defaultdict(list)
        for c in orphan_commits:
            by_author[c.author_id].append(c)

        work_items = []
        for author_id, commits in by_author.items():
            # Sort by time
            commits.sort(key=lambda c: c.committed_at)

            # Sliding window grouping
            current_group: list[Commit] = [commits[0]]
            for c in commits[1:]:
                # Check time gap
                last_time = current_group[-1].committed_at
                if (c.committed_at - last_time) <= window:
                    current_group.append(c)
                else:
                    # Flush current group if > 1 commit
                    if len(current_group) >= 2:
                        wi = self._flush_time_group(
                            author_id, repo_id, current_group, grouped_commit_ids
                        )
                        if wi:
                            work_items.append(wi)
                    else:
                        # Single commit stays ungrouped for Phase 3
                        pass
                    current_group = [c]

            # Flush remaining group
            if len(current_group) >= 2:
                wi = self._flush_time_group(
                    author_id, repo_id, current_group, grouped_commit_ids
                )
                if wi:
                    work_items.append(wi)

        return work_items

    def _flush_time_group(
        self,
        author_id: int,
        repo_id: int,
        commits: list[Commit],
        grouped_commit_ids: set[int],
    ) -> Optional[WorkItem]:
        """Create a work item from a time-window group."""
        # Generate title from first meaningful commit message
        title = self._derive_title(commits)

        wi = self._create_work_item(
            developer_id=author_id,
            repo_id=repo_id,
            pull_request_id=None,
            title=title,
            grouping_method="time_window",
            commits=commits,
        )
        for c in commits:
            grouped_commit_ids.add(c.id)
        return wi

    # ────────────────────────────────────────────────────────────
    #  Phase 3: Lone commits
    # ────────────────────────────────────────────────────────────

    def _group_lone_commits(
        self,
        repo_id: int,
        all_commits: list[Commit],
        grouped_commit_ids: set[int],
    ) -> list[WorkItem]:
        """Each remaining ungrouped commit gets its own WorkItem."""
        work_items = []
        for c in all_commits:
            if c.id in grouped_commit_ids:
                continue

            wi = self._create_work_item(
                developer_id=c.author_id,
                repo_id=repo_id,
                pull_request_id=None,
                title=(c.message or "untitled").split("\n")[0][:200],
                grouping_method="lone",
                commits=[c],
            )
            work_items.append(wi)
            grouped_commit_ids.add(c.id)

        return work_items

    # ────────────────────────────────────────────────────────────
    #  Helpers
    # ────────────────────────────────────────────────────────────

    def _create_work_item(
        self,
        developer_id: Optional[int],
        repo_id: int,
        pull_request_id: Optional[int],
        title: str,
        grouping_method: str,
        commits: list[Commit],
    ) -> WorkItem:
        """Create a WorkItem and link commits."""
        # Aggregate stats
        total_add = sum(c.additions or 0 for c in commits)
        total_del = sum(c.deletions or 0 for c in commits)

        # Unique file count
        file_count = (
            self.db.query(func.count(func.distinct(CommitFile.filename)))
            .filter(CommitFile.commit_id.in_([c.id for c in commits]))
            .scalar()
        ) or 0

        times = [c.committed_at for c in commits if c.committed_at]

        wi = WorkItem(
            developer_id=developer_id,
            repo_id=repo_id,
            pull_request_id=pull_request_id,
            title=title[:500],
            grouping_method=grouping_method,
            start_time=min(times) if times else None,
            end_time=max(times) if times else None,
            commit_count=len(commits),
            total_additions=total_add,
            total_deletions=total_del,
            file_count=file_count,
        )
        self.db.add(wi)
        self.db.flush()

        # Link commits
        for c in commits:
            self.db.add(WorkItemCommit(
                work_item_id=wi.id,
                commit_id=c.id,
            ))

        return wi

    def _update_work_item(self, wi: WorkItem, commits: list[Commit]):
        """Update an existing WorkItem with fresh stats."""
        total_add = sum(c.additions or 0 for c in commits)
        total_del = sum(c.deletions or 0 for c in commits)
        times = [c.committed_at for c in commits if c.committed_at]

        file_count = (
            self.db.query(func.count(func.distinct(CommitFile.filename)))
            .filter(CommitFile.commit_id.in_([c.id for c in commits]))
            .scalar()
        ) or 0

        wi.commit_count = len(commits)
        wi.total_additions = total_add
        wi.total_deletions = total_del
        wi.file_count = file_count
        wi.start_time = min(times) if times else wi.start_time
        wi.end_time = max(times) if times else wi.end_time

    def _derive_title(self, commits: list[Commit]) -> str:
        """Generate a title from commit messages."""
        messages = [
            (c.message or "").split("\n")[0].strip()
            for c in commits
            if c.message and not (c.message or "").startswith("Merge")
        ]
        if messages:
            # Use the most descriptive (longest) message
            return max(messages, key=len)[:200]
        if commits:
            return (commits[0].message or "untitled").split("\n")[0][:200]
        return "untitled"

    # ────────────────────────────────────────────────────────────
    #  Utility: Clear and rebuild
    # ────────────────────────────────────────────────────────────

    def clear_work_items_for_repo(self, repo_id: int) -> int:
        """Delete all work items for a repo (for rebuild)."""
        count = (
            self.db.query(WorkItem)
            .filter_by(repo_id=repo_id)
            .delete(synchronize_session=False)
        )
        self.db.commit()
        logger.info("Cleared %d work items for repo #%d", count, repo_id)
        return count
