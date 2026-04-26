# Phase 8 - Evaluation Run and Wizard

Date: 2026-04-26

## Completed

- Added ORM models for `evaluation_runs` and `evaluation_results`.
- Added base schema entries and `scripts/phase8_evaluations.sql` upgrade script.
- Added `EvaluationService` to orchestrate:
  - parse GitHub repo URL
  - sync repository data
  - rebuild work items
  - run rule-based analysis
  - calculate repo-scoped scores
  - persist evaluation results
  - return report data
- Added API endpoints:
  - `POST /api/evaluations`
  - `GET /api/evaluations`
  - `GET /api/evaluations/{id}`
  - `GET /api/evaluations/{id}/results`
  - `GET /api/evaluations/{id}/report`
- Added admin/lead role guard to create evaluation.
- Added frontend routes:
  - `/evaluations/new`
  - `/evaluations/:id`
  - `/evaluations/:id/report`
- Added repository detail button to start an evaluation for the current repo.

## Notes

- Evaluation currently runs synchronously in the API request to stay within the modular monolith architecture.
- The persisted run/result model is ready for a background worker later without changing the main API shape.
- Report text is a first usable version; richer Vietnamese reporting remains in Phase 10.
