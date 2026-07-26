@echo off
cd /d "%~dp0"
python web_app.py
if errorlevel 1 (
  echo.
  echo Khong the khoi dong. Hay kiem tra Python da duoc cai va thu lai.
  pause
)
