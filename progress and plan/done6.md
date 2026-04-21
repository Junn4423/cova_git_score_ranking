# Engineering Contribution Analytics - Tiến Độ Phase 6

## Tổng quan Phase 6
- **Mục tiêu**: Tự động hóa cài dependency và khởi chạy local cho backend/frontend trên Windows
- **Ngày thực hiện**: 2026-04-22

---

## PHASE 6: Windows Local Automation Scripts

### Bước 6.4: Tạo Script Cài Dependency ✅
- [x] Tạo `install.bat` ở thư mục gốc dự án
- [x] Tự kiểm tra `backend\requirements.txt` và `frontend\package.json`
- [x] Tự tạo `backend\venv` nếu chưa tồn tại
- [x] Cài backend dependencies bằng `backend\venv\Scripts\python.exe -m pip install -r backend\requirements.txt`
- [x] Cài frontend dependencies bằng `npm install` trong `frontend\`
- [x] Có fallback `ensurepip` khi môi trường venv chưa có pip ổn định
- [x] Smoke test:
  - Chạy `.\install.bat` từ root → completed successfully ✅
  - Backend requirements cài thành công vào `backend\venv` ✅
  - Frontend `npm install` completed successfully ✅

### Bước 6.5: Tạo Script Start Backend + Frontend ✅
- [x] Tạo `start.bat` ở thư mục gốc dự án
- [x] Tự tìm Python backend ưu tiên `backend\venv\Scripts\python.exe`
- [x] Mở 2 cửa sổ PowerShell riêng:
  - Backend: `uvicorn app.main:app --host 127.0.0.1 --port 8000`
  - Frontend: `npm run dev -- --host 127.0.0.1 --port 5173`
- [x] Có kiểm tra lỗi cơ bản nếu thiếu `npm`, `python`, hoặc thiếu file cấu hình
- [x] Smoke test:
  - Chạy `.\start.bat` từ root → mở được 2 process BE/FE ✅
  - `GET http://127.0.0.1:8000/health` → healthy ✅
  - `GET http://127.0.0.1:5173` → HTTP 200 ✅

### Bước 6.6: Điều chỉnh Script Theo Lỗi Thực Tế ✅
- [x] Bỏ bước bắt buộc `pip install --upgrade pip` trong `install.bat`
  - Lý do: venv cũ trên máy hiện tại bị lỗi launcher `pip3.10.exe`
- [x] Ép frontend bind `127.0.0.1:5173` trong `start.bat`
  - Lý do: Vite ban đầu bind `::1`, làm smoke test IPv4 fail
- [x] Re-smoke test sau khi sửa script → pass toàn bộ ✅

---

## KẾT QUẢ PHASE 6: ✅ HOÀN THÀNH PHẦN SCRIPT CÀI ĐẶT VÀ KHỞI CHẠY LOCAL

### Files mới:
- `install.bat` — cài backend venv + requirements + frontend npm dependencies
- `start.bat` — khởi chạy backend và frontend cùng lúc bằng 2 cửa sổ PowerShell
- `progress and plan/done6.md` — nhật ký phase 6 cho phần automation script

### Tổng kết:
- Có thể cài dependency toàn dự án bằng 1 lệnh: `.\install.bat`
- Có thể chạy BE + FE cùng lúc bằng 1 lệnh: `.\start.bat`
- Đã smoke test thực tế trên Windows hiện tại
- Script đã xử lý được 2 lỗi môi trường thực tế gặp trong lúc test

---

_Ghi chú: Chỉ đánh dấu [x] khi đã smoke test thành công._
