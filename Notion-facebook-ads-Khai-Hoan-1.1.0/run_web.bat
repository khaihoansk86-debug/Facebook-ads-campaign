@echo off
setlocal
cd /d "%~dp0"

set "PYTHON_BIN="
for /d %%D in ("%LocalAppData%\Python\pythoncore-*") do set "PYTHON_BIN=%%~fD\python.exe"
if defined PYTHON_BIN if exist "%PYTHON_BIN%" (
  "%PYTHON_BIN%" web_app.py
  goto :done
)

if exist "%LocalAppData%\Python\bin\python.exe" (
  "%LocalAppData%\Python\bin\python.exe" web_app.py
  goto :done
)

where py >nul 2>nul
if not errorlevel 1 (
  py -3 web_app.py
  goto :done
)

where python >nul 2>nul
if not errorlevel 1 (
  python web_app.py
  goto :done
)

echo Khong tim thay Python. Hay cai Python 3.11 tro len.
pause
exit /b 1

:done
if errorlevel 1 (
  echo.
  echo Khong the khoi dong. Hay kiem tra Python da duoc cai va thu lai.
  pause
)
