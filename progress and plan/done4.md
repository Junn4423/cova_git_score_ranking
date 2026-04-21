# Engineering Contribution Analytics - Tiến Độ Phase 4

## Tổng quan Phase 4
- **Mục tiêu**: Tuần 4 — Work item grouping + rule engine nền → Commit được gom thành cụm công việc
- **Ngày thực hiện**: 2026-04-21

---

## TUẦN 4: Work Item Grouping + Rule Engine Nền

### Bước 4.1: Tạo Work Item Grouping Service ✅
- [x] Tạo `backend/app/services/grouping.py` — GroupingService class
- [x] Gom theo PR: commit nằm trong PR → 1 work item per PR
- [x] Gom theo thời gian: cùng author + cửa sổ thời gian (cấu hình 4-24h, mặc định 8h)
  - Sliding window algorithm: gap > window → new group
  - Chỉ tạo work item khi >=2 commits gần nhau
- [x] Gom standalone: commit không thuộc nhóm nào → 1 work item riêng
- [x] Tính toán: commit_count, total_additions, total_deletions, file_count (unique), start_time, end_time
- [x] Auto-detect title từ PR title hoặc commit messages (chọn message dài nhất, bỏ Merge)
- [x] Clear & rebuild support (`clear_work_items_for_repo`)
- [x] Cấu hình time window từ `app_configs` table
- [x] Smoke test service:
  - pallets/flask: 100 commits → 35 work items (PR=0, Time Window=19, Lone=16) ✅
  - cova_git_score_ranking: 1 commit → 1 work item ✅

### Bước 4.2: Tạo Work Item API Endpoints ✅
- [x] `POST /api/work-items/build` — trigger gom work items cho repo
  - Body: `{repo_id, rebuild}`, rebuild=true xóa cũ rồi tạo lại
  - Response: `{repo, total_commits, work_items_created, pr_based, time_based, lone}`
- [x] `GET /api/work-items` — list work items (filter by repo_id, developer_id, grouping_method, limit, offset)
  - Trả về: title, developer (avatar, login), repo, method tag, commits, +/-, files, time range
- [x] `GET /api/work-items/{id}` — chi tiết work item + commits liên quan
- [x] `GET /api/work-items/stats` — thống kê work items (total, by_method)
- [x] Smoke test API:
  - POST /api/work-items/build repo_id=2 → 35 work items created ✅
  - GET /api/work-items/stats → total=36, by_method={time_window: 19, lone: 17} ✅
  - GET /api/work-items?limit=3 → 3 items with full data ✅

### Bước 4.3: Tạo Rule Engine Nền (Scoring Foundation) ✅
- [x] Tạo `backend/app/scoring/engine.py` — ScoringEngine class
- [x] Đọc trọng số từ app_configs (`scoring_weights`)
- [x] Tính Activity Score (0-100): 50% active_days + 30% merged_pr_count + 20% review_count
  - active_days normalized: /20 * 100, max 100
  - Each merged PR = 15 points, each review = 10 points
- [x] Tính Quality Score (0-100): 35% meaningful_ratio + 20% non_merge_ratio + 25% coherence + 20% message_quality
  - meaningful_ratio: % commits có file không phải generated/lockfile
  - coherence: ratio commits/work_items (higher = better grouped)
  - message_quality: % commits có message >= 10 chars, not starting with "Merge"
- [x] Tính Impact Score (0-100): 70% lines_score + bugfix_bonus + meaningful_ratio * 10
  - lines_score: meaningful_lines / 2000 * 100, max 100
  - bugfix_bonus: detect fix/bug/hotfix/patch keywords, max 20
- [x] Contribution Score = 15% Activity + 50% Quality + 35% Impact
- [x] Confidence Score = min(1.0, commit_count / 20)
- [x] Top positive/negative reasons generated automatically
- [x] Evidence links (commit count, active days, work items)
- [x] Lưu kết quả vào score_snapshots + score_breakdowns (3 breakdown records per snapshot)
- [x] Delete old snapshot before recalculate (same dev + period)
- [x] Batch scoring: `calculate_all_scores` — all active non-bot devs
- [x] Smoke test engine:
  - POST /api/scores/calculate period_days=90 → 3 developers scored ✅
  - Junn4423: final=71.42 (Activity=2.5, Quality=91.67, Impact=72.03, conf=0.05) ✅
  - davidism: final=68.02 (Activity=35.0, Quality=59.33, Impact=94.59, conf=1.0) ✅
  - adityasah104: final=49.81 (Activity=2.5, Quality=91.67, Impact=10.28, conf=0.05) ✅

### Bước 4.4: Tạo Scoring API Endpoints ✅
- [x] `POST /api/scores/calculate` — trigger tính điểm (single dev or all)
  - Body: `{developer_id?, period_days}`, null developer_id = all
- [x] `GET /api/scores/ranking` — bảng xếp hạng (sorted by final_score desc)
  - Response: rank, developer info, final/activity/quality/impact scores, confidence, reasons
- [x] `GET /api/scores/{dev_id}` — score detail + breakdowns
  - Response: snapshot (scores, reasons, evidence), breakdowns (component, raw, weight, weighted, details)
- [x] Smoke test API:
  - GET /api/scores/ranking?period_days=90 → 3 devs ranked ✅
  - GET /api/scores/2 → davidism detail with 3 breakdowns (activity, quality, impact) ✅

### Bước 4.5: Frontend — Work Items Page ✅
- [x] Trang Work Items: list 36 items với columns: title, developer, method, commits, +/-, files, repo, time range
- [x] Filter by repo, grouping_method
- [x] Stats cards: Total (36), PR-based (0), Time Window (19), Standalone (17)
- [x] Build Work Items button → modal with repo select → trigger rebuild
- [x] Method tags color: PR=purple, Time Window=blue, Standalone=default
- [x] Developer avatars + click → dev detail
- [x] Smoke test UI: Work Items page load, 36 items displayed with stats ✅

### Bước 4.6: Frontend — Ranking Page ✅
- [x] Trang Ranking: bảng xếp hạng developers
- [x] Radar chart cho top 3 contributors (Activity, Quality, Impact, Final)
- [x] Table columns: Rank (#1-3 medals), Developer, Final Score (circle progress), Activity, Quality, Impact, Confidence (progress bar), Highlights (positive/negative reasons)
- [x] Time period filter (7/30/90/180 ngày)
- [x] Calculate Scores button → trigger batch scoring
- [x] Score color coding: ≥80 green, ≥60 blue, ≥40 yellow, <40 red
- [x] Click row → navigate to developer detail
- [x] Formula displayed: "15% Activity + 50% Quality + 35% Impact"
- [x] Smoke test UI: Ranking page load, 3 devs ranked with radar chart ✅

### Bước 4.7: Frontend — Updated Navigation ✅
- [x] Sidebar: Dashboard, **Ranking**, Developers, Repositories, **Work Items**, Pull Requests, Admin
- [x] Version tag: v0.3.0
- [x] All routes: /, /ranking, /developers, /developers/:id, /repositories, /repositories/:id, /work-items, /pull-requests, /admin
- [x] Active menu key detection updated for all new paths
- [x] Smoke test navigation: all sidebar items navigate correctly ✅

---

## KẾT QUẢ TUẦN 4: ✅ HOÀN THÀNH

### Backend mới (3 files):
- `backend/app/services/grouping.py` — GroupingService: 3-phase commit grouping (PR → Time → Lone)
- `backend/app/scoring/engine.py` — ScoringEngine V1: Activity + Quality + Impact scoring
- `backend/app/api/work_items.py` — Work Items API: build, list, detail, stats
- `backend/app/api/scores.py` — Scoring API: calculate, ranking, developer score detail

### Frontend mới (2 pages):
- `WorkItemsPage.tsx` — List, filters, stats, build trigger
- `RankingPage.tsx` — Radar chart, ranking table, score calc, highlights

### Tổng kết:
- Work Item Grouping: 101 commits → 36 work items (19 time-based, 17 standalone)
- Scoring Engine V1: 3-layer scoring formula với configurable weights
- 3 developers scored thành công (Junn4423=71.42, davidism=68.02, adityasah104=49.81)
- 7 API endpoints mới (work-items 4, scores 3)
- 2 frontend pages mới + navigation update
- Radar chart, circle progress, confidence bars
- Tất cả smoke tests passed (Backend API + Frontend UI)

---

_Ghi chú: Chỉ đánh dấu [x] khi đã smoke test thành công._
