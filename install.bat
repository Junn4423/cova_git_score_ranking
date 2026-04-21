@echo off
setlocal

set "ROOT=%~dp0"
set "BACKEND_DIR=%ROOT%backend"
set "FRONTEND_DIR=%ROOT%frontend"
set "VENV_DIR=%BACKEND_DIR%\venv"
set "VENV_PYTHON=%VENV_DIR%\Scripts\python.exe"

echo ========================================
echo Installing dependencies for Cova_Score
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

if exist "%VENV_PYTHON%" goto :install_backend

echo [1/4] Creating backend virtual environment...
where py >nul 2>&1
if not errorlevel 1 (
  py -3.10 -m venv "%VENV_DIR%" >nul 2>&1
  if exist "%VENV_PYTHON%" goto :install_backend
  py -m venv "%VENV_DIR%"
  if exist "%VENV_PYTHON%" goto :install_backend
)

where python >nul 2>&1
if errorlevel 1 (
  echo [ERROR] Python was not found in PATH.
  exit /b 1
)

python -m venv "%VENV_DIR%"
if errorlevel 1 (
  echo [ERROR] Failed to create backend virtual environment.
  exit /b 1
)

:install_backend
echo [2/4] Installing backend dependencies...
"%VENV_PYTHON%" -m pip --version >nul 2>&1
if errorlevel 1 (
  echo [INFO] pip is missing in backend venv. Running ensurepip...
  "%VENV_PYTHON%" -m ensurepip --upgrade
  if errorlevel 1 (
    echo [ERROR] Failed to bootstrap pip in backend venv.
    exit /b 1
  )
)

"%VENV_PYTHON%" -m pip install -r "%BACKEND_DIR%\requirements.txt"
if errorlevel 1 (
  echo [ERROR] Failed to install backend requirements.
  exit /b 1
)

echo [3/4] Installing frontend dependencies...
pushd "%FRONTEND_DIR%"
call npm install
if errorlevel 1 (
  popd
  echo [ERROR] Failed to install frontend dependencies.
  exit /b 1
)
popd

echo [4/4] Dependency installation completed successfully.
echo Backend python: %VENV_PYTHON%
echo Frontend dir: %FRONTEND_DIR%
exit /b 0
