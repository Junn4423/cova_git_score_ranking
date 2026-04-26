# Phase 7 - Repo-scoped scoring

Date: 2026-04-26

## Completed

- Added `repo_id` to `score_snapshots` in ORM and base schema.
- Added `scripts/phase7_repo_scoring.sql` upgrade script for existing MySQL/Laragon databases.
- Updated `ScoringEngine.calculate_score()` to accept `repo_id` and filter commits, PRs, reviews, work items, and AI analysis through the selected repo context.
- Updated `ScoringEngine.calculate_all_scores()` to calculate only developers with commits in the selected repo and period.
- Kept backward-compatible global scoring with `repo_id IS NULL`.
- Updated `/api/scores/calculate`, `/api/scores/ranking`, and `/api/scores/{dev_id}` to accept `repo_id`.
- Added admin/lead role guard to `/api/scores/calculate`.
- Updated Ranking page to require a repository selection or `/ranking?repo_id=ID`.
- Added `scripts/smoke_phase7_repo_scoring.py` to verify that one developer with commits in two repositories gets separate repo-scoped snapshots and rankings.

## Acceptance Notes

- Repo ranking now filters `score_snapshots.repo_id == selected_repo_id`.
- Global ranking, when used through the API without `repo_id`, only reads `repo_id IS NULL`.
- Ranking UI labels the page as `Ranking trong repo <full_name>` after repository selection.
