# FULL PLAN TRIỂN KHAI MỚI
# COVA Git Score Ranking — Engineering Contribution Analytics

**Phiên bản:** v3 sau Phase 6  
**Ngày cập nhật:** 2026-04-26  
**Trạng thái hiện tại:** Phase 1 → Phase 6 đã hoàn thành nền MVP kỹ thuật  
**Stack chốt:** React + TypeScript + Vite, Python FastAPI, MySQL/Laragon, GitHub REST API, optional AI provider

---

## 0. Mục tiêu tài liệu

Tài liệu này thay thế bản `plan_full.txt` cũ và được viết lại theo định hướng sản phẩm mới sau khi source đã hoàn thành đến Phase 6.

Mục tiêu mới không còn là chỉ xây một dashboard thống kê GitHub. Mục tiêu đúng là xây một **hệ thống đánh giá đóng góp theo từng repository/project**, có luồng rõ ràng:

```text
Nhập link repo
→ kiểm tra repo public/private
→ xin quyền truy cập nếu repo private
→ quét dữ liệu GitHub
→ gom commit thành work item
→ chạy rule-based scoring sơ bộ
→ chạy AI analysis
→ tính điểm cuối cùng theo từng repo
→ sinh bảng xếp hạng và nhận xét tiếng Việt cho từng thành viên
```

Nguyên tắc chốt: **điểm số phải có bằng chứng, có giải thích, có confidence, và không được trộn đóng góp của nhiều repo khi người dùng đang đánh giá một repo cụ thể.**

---

## 1. Tóm tắt điều hành

Project hiện đã có nền kỹ thuật tốt: backend FastAPI, frontend React, MySQL schema, GitHub ingestion, dashboard, developer/repository pages, work item grouping, scoring engine, AI/rule-based analysis, admin config, auth nội bộ, script install/start local.

Tuy nhiên, sản phẩm hiện đang lệch khỏi mục tiêu chính ở ba điểm:

1. **Ranking chưa thật sự theo từng repo.** Score hiện chủ yếu tính theo developer + period, dễ bị trộn dữ liệu giữa nhiều repo.
2. **Luồng đánh giá chính chưa rõ.** Người dùng phải tự đi qua nhiều trang như Dashboard, Repositories, Work Items, AI Analysis, Ranking thay vì có một luồng “New Evaluation”.
3. **Private repo access chưa thành flow sản phẩm.** Hệ thống hiện phù hợp với token cấu hình sẵn hơn là flow người dùng nhập repo rồi cấp quyền GitHub.

Do đó, roadmap mới phải ưu tiên sửa lõi sản phẩm trước khi thêm chart, UI phụ hoặc tính năng mở rộng.

---

## 2. Hiện trạng sau Phase 6

### 2.1 Đã hoàn thành

Các phần đã có thể xem là nền kỹ thuật:

- Project structure backend/frontend/config/scripts.
- FastAPI backend, React + Vite frontend.
- MySQL schema với các bảng chính: developers, developer_aliases, repositories, commits, commit_files, pull_requests, reviews, work_items, ai_commit_analysis, score_snapshots, score_breakdowns, app_configs, users, audit_logs, job_queue.
- GitHub API client.
- Sync repo, commits, commit files, PRs, reviews.
- Developer resolver và alias mapping.
- Dashboard overview.
- Developers page và developer detail.
- Repositories page và repository detail.
- Pull Requests page.
- Work item grouping.
- Scoring engine V2: Activity, Quality, Impact, final score, confidence, reasons, breakdown.
- Rule-based AI analyzer: change_type, complexity, risk, message alignment, test presence.
- Admin config và recalculate.
- Auth nội bộ bằng username/password/JWT.
- Script Windows `install.bat` và `start.bat`.

### 2.2 Chưa đạt mục tiêu sản phẩm

Các điểm chưa đạt cần sửa ngay:

- Chưa có `Evaluation Run` làm đơn vị đánh giá chính.
- Chưa có ranking bắt buộc theo `repo_id`.
- `score_snapshots` chưa lưu repo context.
- Ranking API chưa bắt buộc/chưa hỗ trợ tốt `repo_id`.
- UI chưa có flow nhập repo → kiểm tra quyền → scan → analyze → score → report.
- GitHub private repo access chưa có GitHub App/OAuth flow.
- AI hiện mới là rule-based analyzer, chưa có LLM provider production-ready.
- UI tiếng Việt chưa nhất quán.
- Admin/security chưa phủ đều cho các endpoint quan trọng như sync/calculate.
- Chưa có final report tiếng Việt cho từng thành viên trong repo.
- Chưa có README sản phẩm rõ ràng.

---

## 3. Định nghĩa sản phẩm đích

### 3.1 Người dùng chính

- **Admin:** cấu hình hệ thống, GitHub access, scoring weights, user/role, audit.
- **Lead/Manager:** tạo lần đánh giá repo, xem ranking, xem nhận xét từng thành viên, export report.
- **Developer:** xem kết quả cá nhân, bằng chứng, điểm mạnh/yếu, commit/work item liên quan.

### 3.2 Use case chính

Use case quan trọng nhất:

```text
Lead nhập GitHub repo URL
→ hệ thống kiểm tra repo
→ nếu public thì cho sync ngay
→ nếu private thì yêu cầu kết nối GitHub App/OAuth
→ hệ thống quét dữ liệu trong khoảng thời gian chọn
→ hệ thống gom commit thành work item
→ hệ thống phân tích commit/work item bằng rule + AI
→ hệ thống tính score theo từng developer trong repo đó
→ hệ thống sinh ranking cuối cùng và nhận xét tiếng Việt
→ lead xem report, drill-down evidence, export nếu cần
```

### 3.3 Không làm ở giai đoạn này

- Không tích hợp Jira/Linear ngay.
- Không làm mobile app.
- Không train model riêng.
- Không dùng score làm căn cứ thưởng/phạt tuyệt đối.
- Không đánh giá đạo đức, thái độ, hoặc năng lực tổng quát ngoài dữ liệu có bằng chứng.

---

## 4. Nguyên tắc công bằng bắt buộc

1. **Không dùng raw commit count làm thước đo chính.** Commit nhiều không đồng nghĩa đóng góp tốt.
2. **Không dùng raw LOC làm thước đo chính.** Dòng code nhiều có thể là generated, lockfile, formatting hoặc churn.
3. **Phải gom commit thành work item trước khi chấm.** Tránh thưởng sai người commit vụn và phạt oan người commit dồn.
4. **Phải chấm theo repo/project khi đánh giá repo/project.** Không trộn đóng góp từ repo khác vào ranking của repo đang xem.
5. **AI chỉ là lớp phân tích, không phải người quyết định cuối.** Final score phải đi qua rule engine có trọng số rõ ràng.
6. **Mọi điểm số phải có evidence.** Evidence gồm commit, PR, review, work item, file changed, reason, confidence.
7. **Phải có confidence score.** Người có ít dữ liệu không nên được kết luận mạnh.
8. **Phải có cơ chế loại trừ bot, generated file, lockfile, repo không liên quan.**
9. **Phải hỗ trợ alias mapping.** Một người có nhiều email/login phải được quy về cùng developer.
10. **Người dùng phải hiểu vì sao bị cộng/trừ điểm.** Báo cáo phải giải thích bằng tiếng Việt rõ ràng.

---

## 5. Kiến trúc tổng thể mới

```text
[React Internal UI]
  ├─ Evaluation Wizard
  ├─ Repo Ranking Report
  ├─ Developer Evidence View
  ├─ Admin Config
  └─ GitHub Access Settings

        ↓ REST API

[FastAPI Modular Monolith]
  ├─ Auth API
  ├─ GitHub Access API
  ├─ Sync/Ingestion API
  ├─ Evaluation API
  ├─ Work Item API
  ├─ Analysis API
  ├─ Scoring API
  ├─ Report API
  └─ Admin API

        ↓

[MySQL]
  ├─ Raw GitHub data
  ├─ Normalized developers/repos/commits/PRs/reviews
  ├─ Work items
  ├─ AI analysis
  ├─ Score snapshots per repo
  ├─ Evaluation runs
  ├─ Reports
  └─ Audit logs

        ↓ optional

[Worker/Scheduler]
  ├─ sync_repo
  ├─ build_work_items
  ├─ run_analysis
  ├─ calculate_scores
  ├─ generate_report
  └─ cleanup/retry
```

Giai đoạn trước mắt vẫn giữ modular monolith. Chưa cần microservices, chưa cần Docker bắt buộc.

---

## 6. Data model cần chỉnh

### 6.1 Sửa `score_snapshots`

Hiện tại score thiếu repo context. Cần thêm:

```sql
ALTER TABLE score_snapshots
ADD COLUMN repo_id INT NULL AFTER developer_id,
ADD INDEX idx_score_repo_period (repo_id, period_start, period_end),
ADD INDEX idx_score_repo_dev_period (repo_id, developer_id, period_start, period_end);
```

Ý nghĩa:

- `repo_id IS NOT NULL`: score của developer trong một repo cụ thể.
- `repo_id IS NULL`: global profile, chỉ dùng cho tổng quan toàn hệ thống, không dùng làm ranking repo.

### 6.2 Thêm bảng `evaluation_runs`

```sql
CREATE TABLE evaluation_runs (
  id INT AUTO_INCREMENT PRIMARY KEY,
  repo_id INT NOT NULL,
  requested_by_user_id INT NULL,
  status ENUM('pending','running','done','failed','cancelled') NOT NULL DEFAULT 'pending',
  current_step VARCHAR(100) NULL,
  period_start DATE NOT NULL,
  period_end DATE NOT NULL,
  input_repo_url VARCHAR(500) NULL,
  access_mode ENUM('public','server_token','github_app','oauth') NULL,
  sync_started_at DATETIME NULL,
  sync_completed_at DATETIME NULL,
  grouping_completed_at DATETIME NULL,
  analysis_completed_at DATETIME NULL,
  scoring_completed_at DATETIME NULL,
  report_completed_at DATETIME NULL,
  error_message TEXT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  INDEX idx_eval_repo_period (repo_id, period_start, period_end),
  INDEX idx_eval_status (status)
);
```

### 6.3 Thêm bảng `evaluation_results`

```sql
CREATE TABLE evaluation_results (
  id INT AUTO_INCREMENT PRIMARY KEY,
  evaluation_run_id INT NOT NULL,
  developer_id INT NOT NULL,
  repo_id INT NOT NULL,
  rank_no INT NOT NULL,
  final_score DECIMAL(6,2) NOT NULL,
  activity_score DECIMAL(6,2) NULL,
  quality_score DECIMAL(6,2) NULL,
  impact_score DECIMAL(6,2) NULL,
  confidence_score DECIMAL(3,2) NULL,
  summary_vi TEXT NULL,
  strengths JSON NULL,
  weaknesses JSON NULL,
  recommendations JSON NULL,
  evidence JSON NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uq_eval_dev (evaluation_run_id, developer_id),
  INDEX idx_eval_result_repo_rank (repo_id, rank_no)
);
```

### 6.4 Thêm bảng GitHub access nếu dùng GitHub App

```sql
CREATE TABLE github_installations (
  id INT AUTO_INCREMENT PRIMARY KEY,
  installation_id BIGINT NOT NULL UNIQUE,
  account_login VARCHAR(200) NULL,
  account_type VARCHAR(50) NULL,
  permissions JSON NULL,
  repository_selection VARCHAR(50) NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);
```

Nếu chưa làm GitHub App ngay, vẫn chuẩn bị model để không phải đập lại kiến trúc.

---

## 7. Scoring engine mới

### 7.1 Chữ ký hàm bắt buộc

Hiện tại engine cần được sửa từ:

```python
calculate_score(developer_id, period_start, period_end)
```

thành:

```python
calculate_score(
    developer_id: int,
    repo_id: int | None,
    period_start: date,
    period_end: date,
) -> ScoreSnapshot | None
```

Batch scoring:

```python
calculate_all_scores(
    repo_id: int,
    period_start: date,
    period_end: date,
) -> list[ScoreSnapshot]
```

### 7.2 Query dữ liệu bắt buộc filter repo

Khi `repo_id` có giá trị, tất cả dữ liệu scoring phải filter theo repo:

```python
Commit.author_id == developer_id
Commit.repo_id == repo_id
Commit.committed_at >= period_start
Commit.committed_at <= period_end
```

PR, review, work item, AI analysis cũng phải đi qua repo context.

### 7.3 Công thức scoring giữ lại nhưng chuẩn hóa

```text
Final Score = 15% Activity + 50% Quality + 35% Impact
```

#### Activity Score

Tín hiệu:

- active_days trong repo
- merged_pr_count trong repo
- review_count trong repo
- work_item_count trong repo

Không nên thưởng quá mạnh cho commit_count.

#### Quality Score

Tín hiệu:

- meaningful_ratio
- non_merge_ratio
- work_item_coherence
- message_alignment_score
- test_presence
- generated/lockfile exclusion
- PR hygiene nếu có PR

#### Impact Score

Tín hiệu:

- meaningful lines changed
- feature/bugfix/security/performance weight
- complexity-weighted contribution
- delivered PR/work item
- risk-adjusted impact

### 7.4 Confidence Score

```text
confidence = min(1.0, weighted_data_volume / threshold)
```

Dữ liệu có thể gồm:

- số work item
- số commit meaningful
- số PR
- số ngày active
- số analysis result có confidence cao

Không nên chỉ dựa vào commit_count.

### 7.5 Output bắt buộc

Mỗi score phải có:

```json
{
  "developer_id": 1,
  "repo_id": 2,
  "period_start": "2026-01-01",
  "period_end": "2026-04-26",
  "final_score": 82.4,
  "activity_score": 70.0,
  "quality_score": 88.0,
  "impact_score": 84.0,
  "confidence_score": 0.86,
  "top_positive_reasons": [],
  "top_negative_reasons": [],
  "evidence_links": [],
  "score_breakdown": []
}
```

---

## 8. Evaluation flow mới

### 8.1 API chính

```http
POST /api/evaluations
```

Body:

```json
{
  "repo_url": "https://github.com/owner/repo",
  "period_days": 90,
  "max_commit_pages": 5,
  "max_pr_pages": 5,
  "run_analysis": true,
  "force_resync": false
}
```

Response:

```json
{
  "evaluation_run_id": 123,
  "repo_id": 2,
  "status": "running",
  "current_step": "sync_repo"
}
```

### 8.2 Các bước xử lý

```text
1. parse_repo_url
2. check_repo_access
3. upsert_repository
4. sync_commits
5. sync_pull_requests
6. sync_reviews
7. build_work_items
8. run_rule_analysis
9. run_ai_analysis_optional
10. calculate_repo_scores
11. generate_vi_report
12. mark_done
```

### 8.3 API theo dõi trạng thái

```http
GET /api/evaluations/{id}
GET /api/evaluations/{id}/results
GET /api/evaluations/{id}/report
```

### 8.4 UI Wizard

Tạo route:

```text
/evaluations/new
/evaluations/:id
/evaluations/:id/report
```

Wizard gồm:

1. Nhập GitHub repo URL.
2. Chọn khoảng thời gian: 7/30/90/180/365 ngày hoặc custom.
3. Kiểm tra repo public/private.
4. Nếu private: hiển thị hướng dẫn kết nối GitHub App/OAuth.
5. Chạy evaluation và hiển thị progress từng bước.
6. Hiển thị report cuối.

---

## 9. GitHub access strategy

### 9.1 Giai đoạn nhanh

Dùng `GITHUB_TOKEN` server-side read-only để sync repo public hoặc repo private mà admin đã cấp quyền.

Yêu cầu:

- Không hard-code token.
- Token lưu trong `.env` hoặc secret nội bộ.
- Log không được in token.
- Sync API phải yêu cầu role admin/lead.

### 9.2 Giai đoạn chuẩn

Dùng GitHub App.

Flow:

```text
User click “Connect GitHub”
→ chuyển sang GitHub App install page
→ user chọn repo được phép
→ GitHub redirect về callback
→ backend lưu installation_id
→ khi sync repo private, backend tạo installation token tạm thời
→ dùng token đó gọi GitHub API
```

Ưu điểm:

- Quản trị quyền sạch.
- Chọn repo cụ thể.
- Dễ audit.
- Không yêu cầu người dùng tự tạo PAT.
- An toàn hơn cho private repo.

### 9.3 Không khuyến nghị

Không nên yêu cầu người dùng dán Personal Access Token trực tiếp vào UI ở bản ổn định. Nếu bắt buộc hỗ trợ PAT tạm thời, phải encrypt và chỉ admin dùng.

---

## 10. AI analysis strategy

### 10.1 Ba chế độ analysis

```text
rule_based: chạy heuristic hiện tại, không cần API key
llm: dùng AI provider để phân tích diff/PR/work item
hybrid: rule_based trước, AI bổ sung summary/reasoning cho case quan trọng
```

Mặc định giai đoạn gần: `hybrid`.

### 10.2 Đối tượng AI nên phân tích

Ưu tiên theo thứ tự:

1. Work item.
2. Pull request.
3. Commit.

Không nên chỉ phân tích từng commit rời rạc vì dễ mất ngữ cảnh.

### 10.3 JSON output bắt buộc

```json
{
  "summary_vi": "Tóm tắt công việc bằng tiếng Việt",
  "change_type": "feature|bugfix|refactor|test|docs|config|chore|security|performance",
  "complexity_score": 0,
  "risk_score": 0,
  "message_alignment_score": 0,
  "test_presence": true,
  "coherence_score": 0,
  "impact_notes": ["..."],
  "quality_notes": ["..."],
  "confidence": 0.0
}
```

### 10.4 AI không được làm

- Không tự quyết final score.
- Không suy diễn thái độ cá nhân.
- Không phán xét năng lực ngoài dữ liệu GitHub.
- Không tạo lý do nếu không có evidence.

### 10.5 Lưu audit AI

Mỗi analysis phải lưu:

- `model_version`
- `prompt_version`
- `schema_version`
- `raw_response`
- `confidence`
- target type/id

---

## 11. Report tiếng Việt

### 11.1 Mục tiêu report

Report phải trả lời được 4 câu hỏi:

1. Ai đóng góp nhiều và tốt nhất trong repo này?
2. Vì sao người đó có điểm như vậy?
3. Bằng chứng nằm ở commit/PR/work item nào?
4. Người đó nên cải thiện gì?

### 11.2 Cấu trúc report repo

```text
Báo cáo đánh giá repo: owner/repo
Khoảng thời gian: 90 ngày
Ngày tạo: yyyy-mm-dd
Số thành viên có dữ liệu: N
Số commit: N
Số PR: N
Số work item: N

Bảng xếp hạng:
#1 Developer A — 82.40 điểm — Confidence 0.86
#2 Developer B — 76.10 điểm — Confidence 0.73
...

Nhận xét từng người:
- Tổng quan đóng góp
- Điểm mạnh
- Điểm cần cải thiện
- Bằng chứng chính
- Khuyến nghị
```

### 11.3 Cấu trúc nhận xét từng developer

```json
{
  "developer": "username",
  "rank": 1,
  "final_score": 82.4,
  "summary_vi": "Developer này đóng góp chính vào...",
  "strengths": [
    "Có nhiều work item meaningful",
    "Commit message tương đối rõ",
    "Có bổ sung test cho thay đổi quan trọng"
  ],
  "weaknesses": [
    "Một số commit còn quá lớn",
    "Thiếu PR review ở vài thay đổi rủi ro"
  ],
  "recommendations": [
    "Nên tách commit theo từng cụm chức năng nhỏ hơn",
    "Nên bổ sung test cho module có risk cao"
  ],
  "evidence": [
    {
      "type": "commit",
      "sha": "abc123",
      "title": "...",
      "url": "..."
    }
  ]
}
```

---

## 12. Frontend roadmap mới

### 12.1 Navigation mới

Đề xuất menu tiếng Việt:

```text
Tổng quan
Đánh giá repo
Báo cáo
Xếp hạng
Thành viên
Kho mã nguồn
Cụm công việc
Phân tích AI
Pull Requests
Quản trị
```

### 12.2 Trang cần thêm

#### `/evaluations/new` — Tạo đánh giá mới

- Input repo URL.
- Chọn period.
- Chọn options: fetch files, run AI, force resync.
- Kiểm tra access.
- Button “Bắt đầu đánh giá”.

#### `/evaluations/:id` — Tiến trình đánh giá

- Stepper progress.
- Log tóm tắt từng bước.
- Trạng thái lỗi/retry.
- Link đến report khi xong.

#### `/evaluations/:id/report` — Báo cáo cuối

- Summary repo.
- Ranking table.
- Score breakdown.
- Nhận xét tiếng Việt từng người.
- Evidence links.
- Export Markdown/PDF/Excel sau này.

### 12.3 Trang cần chỉnh

#### Ranking Page

- Bắt buộc chọn repo hoặc đi từ evaluation report.
- Không mặc định hiển thị global ranking nếu mục tiêu là đánh giá repo.
- Có label rõ: “Ranking trong repo X”.

#### Repository Detail

- Thêm nút “Đánh giá repo này”.
- Hiển thị các evaluation runs gần nhất.

#### Dashboard

- Đổi vai trò thành tổng quan hệ thống.
- Không để dashboard là nơi chính để chạy toàn bộ flow.

---

## 13. Backend roadmap mới

### 13.1 API cần thêm

```http
POST /api/evaluations
GET /api/evaluations
GET /api/evaluations/{id}
GET /api/evaluations/{id}/results
GET /api/evaluations/{id}/report
POST /api/evaluations/{id}/rerun
```

### 13.2 API cần sửa

```http
POST /api/scores/calculate
```

Thêm `repo_id`:

```json
{
  "repo_id": 2,
  "developer_id": null,
  "period_days": 90
}
```

```http
GET /api/scores/ranking?repo_id=2&period_days=90
```

Ranking repo phải ưu tiên snapshots có `repo_id` đúng.

### 13.3 Permission bắt buộc

Các endpoint sau phải yêu cầu `admin` hoặc `lead`:

- sync repo
- build work items
- run analysis
- calculate scores
- create evaluation
- rerun evaluation
- admin config

Developer thường chỉ được xem dữ liệu được phép.

---

## 14. Security checklist

- Không hard-code token/API key.
- Không log token/API key.
- Admin endpoint phải có role guard.
- Sync/calculate/evaluation endpoint phải có role guard.
- GitHub private repo phải đi qua token có scope tối thiểu.
- Audit log mọi thao tác cấu hình score, sync private repo, rerun evaluation.
- CORS không nên để `*` trong bản deploy nội bộ ổn định.
- `.env.example` không chứa secret thật.
- Report không hiển thị dữ liệu repo private cho user không có quyền.

---

## 15. Kế hoạch triển khai từ Phase 7

## Phase 7 — Sửa lõi scoring theo repo

**Mục tiêu:** Ranking trong một repo phải đúng, không bị trộn dữ liệu nhiều repo.

### Việc cần làm

- Thêm `repo_id` vào `score_snapshots`.
- Thêm migration hoặc SQL upgrade script.
- Sửa `ScoringEngine.calculate_score()` nhận `repo_id`.
- Sửa toàn bộ query activity/quality/impact filter theo repo.
- Sửa `calculate_all_scores()` nhận `repo_id`.
- Sửa `POST /api/scores/calculate` nhận `repo_id`.
- Sửa `GET /api/scores/ranking` nhận `repo_id`.
- Sửa frontend RankingPage bắt buộc chọn repo.
- Thêm test/smoke test: cùng một dev có commit ở 2 repo thì ranking repo chỉ tính đúng repo đang chọn.

### Tiêu chí hoàn thành

- Ranking repo A không lấy commit repo B.
- Score detail hiển thị repo context.
- Old global ranking nếu còn thì phải ghi rõ “Toàn hệ thống”.

---

## Phase 8 — Evaluation Run + Wizard

**Mục tiêu:** Tạo luồng chính đúng sản phẩm.

### Việc cần làm

- Thêm bảng `evaluation_runs`.
- Thêm bảng `evaluation_results`.
- Tạo `EvaluationService`.
- Tạo API create/get/report evaluation.
- Tạo frontend `/evaluations/new`.
- Tạo frontend `/evaluations/:id` hiển thị progress.
- Tạo frontend `/evaluations/:id/report`.
- Repository detail thêm nút “Đánh giá repo này”.

### Tiêu chí hoàn thành

- Người dùng có thể nhập repo URL và chạy một lần đánh giá end-to-end.
- Mỗi lần đánh giá có ID, trạng thái, kết quả, report cố định.

---

## Phase 9 — GitHub Access Flow

**Mục tiêu:** Hỗ trợ private repo đúng cách.

### Việc cần làm

- Parse repo URL chuẩn.
- Check public/private/access denied.
- Nếu public: sync ngay.
- Nếu private và server token có quyền: sync.
- Nếu private và chưa có quyền: hiển thị hướng dẫn connect GitHub.
- Chuẩn bị GitHub App installation model.
- Thêm GitHub App/OAuth flow nếu đủ thời gian.

### Tiêu chí hoàn thành

- Repo public chạy mượt.
- Repo private không lỗi mơ hồ; hệ thống nói rõ thiếu quyền và cần kết nối.
- Không yêu cầu user dán PAT ở flow chính.

---

## Phase 10 — Report tiếng Việt + i18n tối thiểu

**Mục tiêu:** Kết quả dùng được cho lead/manager Việt Nam.

### Việc cần làm

- Việt hóa menu chính.
- Việt hóa message, empty state, button, table label.
- Tạo report tiếng Việt cho repo.
- Sinh nhận xét từng developer từ score_breakdown + AI analysis.
- Evidence links rõ ràng.
- Export Markdown trước; PDF/Excel để phase sau.

### Tiêu chí hoàn thành

- Một người không đọc code vẫn hiểu ai làm gì, vì sao được điểm đó.
- Report không chỉ có điểm số mà có nhận xét và bằng chứng.

---

## Phase 11 — AI Provider thật + Hybrid Analysis

**Mục tiêu:** Nâng rule-based analyzer thành hybrid AI analysis.

### Việc cần làm

- Tạo abstraction `AIProvider`.
- Giữ `RuleBasedProvider` hiện tại.
- Thêm `OpenAIProvider` hoặc provider tương đương.
- Tạo prompt versioned.
- Validate JSON schema.
- Retry/fallback khi AI lỗi.
- Config bật/tắt AI trong Admin.
- Chỉ gọi AI cho work item/PR ưu tiên, tránh tốn chi phí.

### Tiêu chí hoàn thành

- Không có API key vẫn chạy rule-based.
- Có API key thì sinh summary/notes tiếng Việt tốt hơn.
- AI lỗi không làm hỏng toàn bộ evaluation.

---

## Phase 12 — Hardening và nghiệm thu nội bộ

**Mục tiêu:** Chạy ổn định, có thể demo và dùng thử nội bộ.

### Việc cần làm

- Role guard đầy đủ.
- Audit log đầy đủ.
- README mới.
- `.env.example` đầy đủ.
- Test dữ liệu mẫu.
- Smoke test script.
- CORS production config.
- Error handling rõ cho GitHub rate limit/access denied.
- Tối ưu query nếu repo lớn.

### Tiêu chí hoàn thành

- Clone repo → install → start → chạy được local.
- Tạo evaluation repo public thành công.
- Xem report cuối thành công.
- Lead có thể dùng kết quả để thảo luận, không phải để phán quyết tuyệt đối.

---

## 16. Acceptance Criteria cho MVP mới

MVP mới chỉ được coi là đạt khi có đủ:

1. Nhập GitHub repo URL từ UI.
2. Kiểm tra access repo rõ ràng.
3. Sync được commit/PR/review/file changes.
4. Build được work items.
5. Run được rule-based analysis.
6. Calculate score theo repo.
7. Ranking không trộn repo.
8. Có report tiếng Việt theo từng developer.
9. Có evidence links.
10. Có confidence score.
11. Admin/lead mới được chạy evaluation/recalculate.
12. Có README hướng dẫn chạy và giải thích công thức.

---

## 17. Thứ tự ưu tiên tuyệt đối

Không phát triển thêm chart hoặc UI phụ trước khi xong các việc này:

```text
1. Scoring theo repo
2. Evaluation Run
3. Evaluation Wizard
4. Report tiếng Việt
5. GitHub access flow cho private repo
```

Đây là xương sống sản phẩm. Làm lệch thứ tự này sẽ khiến project đẹp hơn nhưng không giải quyết đúng bài toán.

---

## 18. Cấu trúc file gợi ý sau khi refactor

```text
backend/app/
  api/
    evaluations.py
    github_access.py
    scores.py
    reports.py
  services/
    evaluation_service.py
    report_service.py
    ingestion.py
    grouping.py
  scoring/
    engine.py
    formulas.py
  ai/
    analyzer.py
    providers/
      base.py
      rule_based.py
      openai_provider.py
  github/
    client.py
    app_client.py
  migrations/
    phase7_repo_scoring.sql

frontend/src/
  pages/
    evaluations/
      NewEvaluationPage.tsx
      EvaluationProgressPage.tsx
      EvaluationReportPage.tsx
    RankingPage.tsx
    RepositoryDetailPage.tsx
  components/
    evaluation/
      RepoUrlInput.tsx
      EvaluationStepper.tsx
      ScoreBreakdownPanel.tsx
      DeveloperReportCard.tsx
```

---

## 19. Prompt cho Agent Code

Dùng prompt sau để yêu cầu agent code triển khai theo kế hoạch này:

```text
Bạn là senior full-stack engineer. Hãy đọc kỹ file `progress and plan/plan_full.md` và triển khai project theo roadmap mới sau Phase 6.

Bối cảnh:
- Project hiện đã có React + TypeScript + Vite frontend, FastAPI backend, MySQL/Laragon database.
- Các phase 1–6 đã hoàn thành nền kỹ thuật: ingestion GitHub, dashboard, developers, repositories, work items, scoring V2, rule-based AI analysis, admin config, auth nội bộ, install/start scripts.
- Vấn đề lớn hiện tại: scoring/ranking đang có nguy cơ bị tổng hợp toàn hệ thống, chưa đánh giá đúng theo từng repo; chưa có Evaluation Run/Wizard; private repo access chưa rõ; report tiếng Việt chưa hoàn chỉnh.

Mục tiêu triển khai trước mắt:
1. Ưu tiên Phase 7 trước: sửa scoring/ranking theo `repo_id`.
2. Không thêm chart/UI phụ trước khi ranking theo repo chạy đúng.
3. Thêm migration hoặc SQL upgrade để `score_snapshots` có `repo_id` và index phù hợp.
4. Sửa `ScoringEngine.calculate_score()` và `calculate_all_scores()` để nhận `repo_id` và filter mọi dữ liệu theo repo khi repo_id được truyền vào.
5. Sửa API `/api/scores/calculate` và `/api/scores/ranking` để nhận `repo_id`.
6. Sửa frontend RankingPage để bắt buộc chọn repo hoặc nhận repo từ query/route; label rõ “Ranking trong repo X”.
7. Thêm smoke test hoặc script kiểm tra: một developer có dữ liệu ở nhiều repo thì ranking repo chỉ tính dữ liệu của repo đang chọn.

Ràng buộc kỹ thuật:
- Giữ kiến trúc modular monolith hiện tại.
- Không phá các API cũ nếu không cần; nếu thay đổi thì giữ backward-compatible càng nhiều càng tốt.
- Không hard-code secret/token.
- Các endpoint sync/calculate/recalculate/evaluation phải có role guard admin/lead nếu chỉnh đến phần đó.
- Code phải rõ ràng, dễ đọc, có error handling cơ bản.
- Sau mỗi phase nhỏ, cập nhật file tiến độ mới trong `progress and plan/`.

Sau khi xong Phase 7, tiếp tục Phase 8:
- Thêm `evaluation_runs` và `evaluation_results`.
- Tạo `EvaluationService`.
- Tạo API tạo/theo dõi/lấy report evaluation.
- Tạo UI wizard: nhập repo URL → chạy evaluation → xem report.

Hãy bắt đầu bằng việc inspect source hiện tại, xác định file cần sửa, rồi triển khai Phase 7 trước. Không triển khai lan man ngoài phạm vi Phase 7 nếu chưa hoàn thành tiêu chí nghiệm thu của Phase 7.
```

---

## 20. Kết luận

Sau Phase 6, project không cần thêm tính năng phụ. Việc quan trọng là kéo nó về đúng sản phẩm:

```text
Công cụ đánh giá đóng góp theo từng repo, có luồng chạy rõ ràng, có điểm số, có nhận xét tiếng Việt, có bằng chứng, có confidence, và có cơ chế truy cập repo private an toàn.
```

Nếu Phase 7 và Phase 8 được làm đúng, project sẽ chuyển từ một dashboard analytics khá tốt thành một sản phẩm contribution evaluation có thể dùng thực tế.
