@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if errorlevel 1 (
  echo Please install Python 3.11 or newer from python.org with the Python Launcher.
  pause
  exit /b 1
)
if not exist .venv\Scripts\python.exe (
  py -3 -m venv .venv
  if errorlevel 1 exit /b 1
)
.venv\Scripts\python.exe -m pip install -r requirements-lock.txt
if errorlevel 1 (
  echo Dependency installation failed. Check your network and Python version.
  pause
  exit /b 1
)
echo Open http://127.0.0.1:8000 in your browser. Press Ctrl+C to stop.
.venv\Scripts\python.exe -m uvicorn wenmai.app:app --host 127.0.0.1 --port 8000
pause
