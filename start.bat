@echo off
setlocal

set "ROOT=%~dp0"
set "BACKEND_DIR=%ROOT%backend"
set "FRONTEND_DIR=%ROOT%frontend"
set "VENV_PYTHON=%BACKEND_DIR%\venv\Scripts\python.exe"

echo ========================================
echo Starting backend and frontend
echo Root: %ROOT%
echo ========================================

if not exist "%BACKEND_DIR%\requirements.txt" (
  echo [ERROR] Missing backend\requirements.txt
  exit /b 1
)

if not exist "%FRONTEND_DIR%\package.json" (
  echo [ERROR] Missing frontend\package.json
  exit /b 1
)

where npm >nul 2>&1
if errorlevel 1 (
  echo [ERROR] npm was not found in PATH.
  exit /b 1
)

if exist "%VENV_PYTHON%" (
  set "BACKEND_PYTHON=%VENV_PYTHON%"
) else (
  where py >nul 2>&1
  if not errorlevel 1 (
    set "BACKEND_PYTHON=py"
  ) else (
    where python >nul 2>&1
    if errorlevel 1 (
      echo [ERROR] No Python executable found. Run install.bat first.
      exit /b 1
    )
    set "BACKEND_PYTHON=python"
  )
)

echo [1/2] Launching backend on http://127.0.0.1:8000
start "Cova Backend" powershell -NoExit -ExecutionPolicy Bypass -Command "Set-Location -LiteralPath '%BACKEND_DIR%'; & '%BACKEND_PYTHON%' -m uvicorn app.main:app --host 127.0.0.1 --port 8000"
if errorlevel 1 (
  echo [ERROR] Failed to start backend window.
  exit /b 1
)

echo [2/2] Launching frontend on http://127.0.0.1:5173
start "Cova Frontend" powershell -NoExit -ExecutionPolicy Bypass -Command "Set-Location -LiteralPath '%FRONTEND_DIR%'; npm run dev -- --host 127.0.0.1 --port 5173"
if errorlevel 1 (
  echo [ERROR] Failed to start frontend window.
  exit /b 1
)

echo Both services were launched in separate windows.
echo If dependency errors appear, run install.bat first.
exit /b 0
