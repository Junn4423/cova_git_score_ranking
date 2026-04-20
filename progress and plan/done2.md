# Engineering Contribution Analytics - Tiến Độ Phase 2

## Tổng quan Phase 2
- **Mục tiêu**: Tuần 2 — Ingestion repo/commit/PR cơ bản, đồng bộ dữ liệu thô về DB
- **Ngày thực hiện**: 2026-04-21

---

## TUẦN 2: Ingestion Module — Đồng bộ dữ liệu GitHub về MySQL

### Bước 2.1: Tạo Ingestion Service ✅
- [x] Tạo `backend/app/services/ingestion.py` — IngestionService class
- [x] Developer resolver: tự động tìm/tạo developer từ GitHub login, email, name
- [x] Alias mapping: đăng ký alias (email + github_login) cho mỗi developer mới
- [x] sync_repositories(): đồng bộ danh sách repos từ org
- [x] sync_single_repo(): đồng bộ 1 repo theo full_name
- [x] sync_commits(): fetch commits + commit files (additions/deletions/patch)
  - Auto-detect lockfile (package-lock.json, yarn.lock, etc.)
  - Auto-detect generated files (.min.js, .map, etc.)
  - Parse committed_at, parent_count, is_merge
  - Fetch detailed commit stats (additions, deletions, total_changes)
- [x] sync_pull_requests(): fetch PRs + link PR↔commits + sync reviews
- [x] full_sync_repo(): end-to-end sync (repo → commits → PRs → reviews)
- [x] Smoke test: sync `Junn4423/cova_git_score_ranking` thành công → 1 commit, 1 developer ✅
- [x] Smoke test: sync `pallets/flask` → 100 commits, 11 developers mới (rate limit 429 sau đó là bình thường) ✅

### Bước 2.2: Tạo Sync API Endpoints ✅
- [x] `POST /api/sync/repo` — trigger sync 1 repo (full_name, max pages, fetch_files)
- [x] `GET /api/sync/stats` — trả về counts: repos, devs, commits, PRs, reviews
- [x] `GET /api/sync/repositories` — list all synced repos
- [x] `GET /api/sync/developers` — list all devs + commit count
- [x] `GET /api/sync/commits` — list recent commits (filter by repo_id, limit)
- [x] Đăng ký sync_router vào main.py
- [x] Smoke test API: POST sync → response `{repo, new_commits, new_prs, total_developers}` ✅
- [x] Smoke test API: GET stats → `{repositories: 2, developers: 12, commits: 101}` ✅
- [x] Smoke test API: GET developers → 12 devs với commit_count ✅
- [x] Smoke test API: GET commits → 20 commits gần nhất, có SHA, author, additions/deletions ✅

### Bước 2.3: Verify dữ liệu MySQL ✅
- [x] 2 repositories (Junn4423/cova_git_score_ranking + pallets/flask)
- [x] 12 developers (auto-created từ GitHub data, có email, avatar)
- [x] 101 commits (có author_id, additions, deletions, is_merge)
- [x] 244 commit_files (có filename, status, additions, deletions, is_generated, is_lockfile)
- [x] developer_aliases đã ghi (email + github_login aliases)
- [x] repositories.last_synced_at đã cập nhật

### Bước 2.4: Update Frontend Dashboard ✅
- [x] Thêm API functions: getSyncStats, getRepositories, getDevelopers, getCommits, syncRepo
- [x] Dashboard hiển thị số liệu thật: 2 repos, 12 devs, 101 commits
- [x] Form "Đồng Bộ Repository": nhập owner/repo → gọi POST sync → refresh data
- [x] Bảng Developers: avatar, login, email, commit_count (sorted)
- [x] Bảng Recent Commits: SHA, author, message, +/- additions/deletions, repo, date
- [x] Smoke test: Dashboard localhost:5173 hiển thị đầy đủ dữ liệu thật ✅

---

## KẾT QUẢ TUẦN 2: ✅ HOÀN THÀNH
- Ingestion service đồng bộ repos, commits (+ files), PRs, reviews từ GitHub
- Developer auto-resolve + alias mapping
- Detect lockfiles + generated files
- REST API đầy đủ cho sync operations
- Dashboard hiển thị dữ liệu thật: bảng developers, commits
- Dữ liệu MySQL verified: 2 repos, 12 devs, 101 commits, 244 commit files

---

_Ghi chú: Chỉ đánh dấu [x] khi đã smoke test thành công._
