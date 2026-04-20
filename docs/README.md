# Engineering Contribution Analytics

Công cụ nội bộ phân tích và đánh giá mức độ đóng góp của lập trình viên dựa trên dữ liệu từ GitHub (Commits, PRs, Reviews, Diffs).

---

## 🚀 Trạng thái dự án: Giai đoạn 1 (Tuần 1) - Khởi tạo & Cấu trúc

Dự án đã hoàn thành thiết lập nền tảng kỹ thuật, cấu trúc thư mục và kết nối giữa các thành phần Backend, Frontend và Database.

### Các thành phần đã triển khai:
- **Backend**: FastAPI (Python) với cấu trúc Modular Monolith.
- **Frontend**: React + Vite + TypeScript + Ant Design.
- **Database**: MySQL (19 bảng nghiệp vụ & cấu hình).
- **GitHub Integration**: Client kết nối GitHub REST API.
- **Security**: Quản lý biến môi trường qua `.env`.

---

## 🛠️ Công nghệ sử dụng

| Lớp | Công nghệ |
| :--- | :--- |
| **Backend** | Python 3.9+, FastAPI, SQLAlchemy 2.0, Pydantic v2 |
| **Frontend** | React 18, TypeScript, Vite, Ant Design (v5), Axios |
| **Database** | MySQL 8.4 (Laragon), Alembic (ready) |
| **API Client** | Httpx (Backend), React Query (Frontend) |

---

## 📁 Cấu trúc thư mục

```text
Cova_Score/
├── backend/            # FastAPI Project
│   ├── app/            # Source code (API, Models, Services, Workers)
│   └── venv/           # Python Virtual Environment
├── frontend/           # React + Vite Project
│   ├── src/            # Components, Pages, API Clients
│   └── node_modules/   # Node dependencies
├── config/             # Cấu hình môi trường (.env, .env.example)
├── scripts/            # Script hỗ trợ (Schema SQL, Migration, Test)
├── storage/            # Lưu trữ logs, exports, raw payloads
└── docs/               # Tài liệu dự án & Plan
```

---

## ⚙️ Hướng dẫn cài đặt & Chạy local

### 1. Yêu cầu hệ thống
- Laragon (MySQL 8+)
- Python 3.9+
- Node.js 20+

### 2. Cài đặt Database
- Mở Laragon, tạo database: `eng_analytics`.
- Import schema: `scripts/schema.sql`.

### 3. Cấu hình Backend
- Truy cập `backend/`, tạo venv và cài đặt:
  ```bash
  python -m venv venv
  .\venv\Scripts\activate
  pip install -r requirements.txt
  ```
- Cấu hình file `config/.env` từ `config/.env.example`.

### 4. Cài đặt Frontend
- Truy cập `frontend/`:
  ```bash
  npm install
  ```

### 5. Khởi chạy
- **Backend**: `uvicorn app.main:app --reload` (tại `backend/`)
- **Frontend**: `npm run dev` (tại `frontend/`)

---

## 📈 Dashboard Hiện tại
Truy cập `http://localhost:5173` để xem trạng thái hệ thống:
- ✅ Health check API
- ✅ Kết nối Database thành công
- ✅ Layout Navigation & Sidebar

---

## 🗓️ Roadmap tiếp theo (Tuần 2)
- Triển khai Ingestion Module (Đồng bộ Repos/Commits/PRs).
- Xây dựng logic Mapping Alias cho Developer.
- Hệ thống Background Jobs đồng bộ định kỳ.

---
*Ghi chú: Đây là công cụ nội bộ, dữ liệu và API Key cần được bảo mật.*
