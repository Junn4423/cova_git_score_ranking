# Engineering Contribution Analytics - Tiến Độ Triển Khai

## Tổng quan
- **Stack**: React + TypeScript + Vite 5 (FE) | Python 3.9 + FastAPI (BE) | MySQL 8.4 Laragon (DB)
- **Plan version**: v2
- **Bắt đầu**: 2026-04-21

---

## TUẦN 1: Khởi tạo dự án, chốt schema, kết nối GitHub

### Bước 1.1: Tạo cấu trúc thư mục dự án ✅
- [x] Tạo folder structure theo Phụ lục A (frontend/, backend/, scripts/, docs/, storage/, config/)
- [x] Khởi tạo frontend (React + Vite 5 + TypeScript) — dùng Vite 5 vì Node 20.14
- [x] Khởi tạo backend (Python FastAPI) — venv + requirements.txt
- [x] Tạo file .env mẫu (config/.env + config/.env.example)

### Bước 1.2: Setup MySQL schema ✅
- [x] Tạo database `eng_analytics` trên Laragon MySQL 8.4
- [x] Tạo 19 bảng: developers, developer_aliases, teams, team_members, repositories, commits, commit_files, pull_requests, pull_request_commits, reviews, work_items, work_item_commits, ai_commit_analysis, score_snapshots, score_breakdowns, app_configs, job_queue, audit_logs, users
- [x] Tạo indexes theo 11.2 (unique, composite, time-based)
- [x] Insert default configs (scoring_weights, sync_interval, etc.)
- [x] Smoke test: `SHOW TABLES` trả về 19 bảng, configs có dữ liệu ✅

### Bước 1.3: Setup Backend FastAPI cơ bản ✅
- [x] Cài đặt dependencies: FastAPI 0.115, SQLAlchemy 2.0, Alembic, Pydantic, Uvicorn, APScheduler, httpx, etc.
- [x] Cấu hình kết nối MySQL (pydantic-settings load từ config/.env)
- [x] Tạo models SQLAlchemy cho tất cả 19 bảng (backend/app/models/models.py)
- [x] Tạo health check endpoint (GET /health — kiểm tra DB connection)
- [x] Smoke test: Uvicorn chạy port 8000, GET /health trả về `{"status":"healthy","database":{"connected":true}}` ✅

### Bước 1.4: Kết nối GitHub API ✅
- [x] Tạo GitHub API client bằng httpx (backend/app/github/client.py)
- [x] Hỗ trợ: list repos, get repo, list commits, get commit, list PRs, get PR, list reviews, rate limit
- [x] Có pagination helper (_get_paginated)
- [x] Smoke test (scripts/test_github.py — public endpoints):
  - Rate limit: 60/60 ✅
  - Get repo facebook/react: 244587 stars ✅
  - List 100 commits ✅
  - List 100 PRs ✅

### Bước 1.5: Setup Frontend React cơ bản ✅
- [x] Khởi tạo Vite 5 + React + TypeScript
- [x] Cài Ant Design, @ant-design/icons, Axios, @tanstack/react-query, react-router-dom, recharts
- [x] Tạo layout: Sidebar (5 menu items) + Header + Content + Footer
- [x] Tạo API client (src/api/client.ts) kết nối backend
- [x] Tạo DashboardPage: hiển thị health status, DB connection, service info, version
- [x] Google Inter font, CSS reset
- [x] Smoke test: FE chạy localhost:5173, gọi BE thành công, hiển thị dashboard đẹp ✅

---

## KẾT QUẢ TUẦN 1: ✅ HOÀN THÀNH
- Backend API chạy tại http://localhost:8000
- Frontend dashboard chạy tại http://localhost:5173
- MySQL 19 bảng + default configs
- GitHub API client tested OK
- Tất cả smoke tests passed

---

_Ghi chú: Chỉ đánh dấu [x] khi đã smoke test thành công._
