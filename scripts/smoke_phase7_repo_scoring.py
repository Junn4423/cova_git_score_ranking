"""
Smoke test for Phase 7 repository-scoped scoring.

It seeds one developer with commits in two repositories and verifies that
repo-specific snapshots keep separate repo_id values and evidence counts.
This test uses an in-memory SQLite database and does not touch local MySQL.
"""

from __future__ import annotations

import sys
from datetime import date, datetime, timedelta
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.core.database import Base  # noqa: E402
from app.models.models import Commit, CommitFile, Developer, Repository, ScoreSnapshot  # noqa: E402
from app.scoring.engine import ScoringEngine  # noqa: E402


def add_commit(
    db,
    repo: Repository,
    dev: Developer,
    sha: str,
    committed_at: datetime,
    additions: int,
    deletions: int,
) -> Commit:
    commit = Commit(
        repo_id=repo.id,
        sha=sha,
        author_id=dev.id,
        committer_id=dev.id,
        message=f"Implement meaningful change {sha}",
        committed_at=committed_at,
        additions=additions,
        deletions=deletions,
        total_changes=additions + deletions,
        parent_count=1,
        is_merge=False,
    )
    db.add(commit)
    db.flush()
    db.add(
        CommitFile(
            commit_id=commit.id,
            filename=f"src/{sha}.py",
            additions=additions,
            deletions=deletions,
            changes=additions + deletions,
            is_generated=False,
            is_lockfile=False,
        )
    )
    return commit


def main() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()

    today = date.today()
    period_start = today - timedelta(days=90)
    period_end = today

    alice = Developer(github_login="alice", display_name="Alice", is_active=True, is_bot=False)
    repo_api = Repository(github_id=1001, full_name="acme/api", name="api")
    repo_web = Repository(github_id=1002, full_name="acme/web", name="web")
    db.add_all([alice, repo_api, repo_web])
    db.flush()

    add_commit(db, repo_api, alice, "a" * 40, datetime.utcnow() - timedelta(days=5), 30, 10)
    for index in range(5):
        add_commit(
            db,
            repo_web,
            alice,
            f"{index + 1:040d}",
            datetime.utcnow() - timedelta(days=index + 1),
            280,
            40,
        )
    db.commit()

    scoring = ScoringEngine(db)
    api_snaps = scoring.calculate_all_scores(repo_api.id, period_start, period_end)
    web_snaps = scoring.calculate_all_scores(repo_web.id, period_start, period_end)

    assert len(api_snaps) == 1, f"expected one api snapshot, got {len(api_snaps)}"
    assert len(web_snaps) == 1, f"expected one web snapshot, got {len(web_snaps)}"

    api_snapshot = (
        db.query(ScoreSnapshot)
        .filter_by(
            developer_id=alice.id,
            repo_id=repo_api.id,
            period_start=period_start,
            period_end=period_end,
        )
        .one()
    )
    web_snapshot = (
        db.query(ScoreSnapshot)
        .filter_by(
            developer_id=alice.id,
            repo_id=repo_web.id,
            period_start=period_start,
            period_end=period_end,
        )
        .one()
    )

    assert api_snapshot.repo_id == repo_api.id
    assert web_snapshot.repo_id == repo_web.id
    assert "Commits: 1" in (api_snapshot.evidence_links or [])
    assert "Commits: 5" in (web_snapshot.evidence_links or [])
    assert web_snapshot.final_score > api_snapshot.final_score

    api_ranking = (
        db.query(ScoreSnapshot)
        .filter_by(repo_id=repo_api.id, period_start=period_start, period_end=period_end)
        .order_by(ScoreSnapshot.final_score.desc())
        .all()
    )
    assert all(snapshot.repo_id == repo_api.id for snapshot in api_ranking)

    print("Phase 7 smoke passed: repo ranking uses only the selected repo.")


if __name__ == "__main__":
    main()
