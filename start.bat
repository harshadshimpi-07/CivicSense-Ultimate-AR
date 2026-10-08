@echo off
cd /d "%~dp0"
title CivicSense Advanced Prototype

echo ==============================================
echo       CIVICSENSE ADVANCED PROTOTYPE
echo ==============================================
echo.

where py >nul 2>nul
if %errorlevel%==0 (
  set PYTHON_CMD=py
) else (
  where python >nul 2>nul
  if %errorlevel%==0 (
    set PYTHON_CMD=python
  ) else (
    echo Python was not found.
    echo Install Python and enable "Add Python to PATH".
    pause
    exit /b 1
  )
)

if not exist .venv (
  echo [1/3] Creating virtual environment...
  %PYTHON_CMD% -m venv .venv
)

call .venv\Scripts\activate.bat

echo [2/3] Installing/checking packages...
python -m pip install -r requirements.txt
if errorlevel 1 (
  echo.
  echo Package installation failed. Check your internet connection.
  pause
  exit /b 1
)

echo [3/3] Starting CivicSense...
echo.
echo Citizen Portal:        http://127.0.0.1:8000/
echo Track Report:          http://127.0.0.1:8000/track
echo Municipality Console:  http://127.0.0.1:8000/admin
echo API Documentation:     http://127.0.0.1:8000/docs
echo.
echo Keep this window open while using CivicSense.
echo Press CTRL+C to stop the server.
echo.
python -m uvicorn main:app --reload
pause
