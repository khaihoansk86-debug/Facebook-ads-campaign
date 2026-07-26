@echo off
setlocal
cd /d "%~dp0"

set "PYTHON_BIN="
for /d %%D in ("%LocalAppData%\Python\pythoncore-*") do set "PYTHON_BIN=%%~fD\python.exe"
if defined PYTHON_BIN if exist "%PYTHON_BIN%" (
    "%PYTHON_BIN%" "%~dp0gui_app.py"
    goto :eof
)

if exist "%LocalAppData%\Python\bin\python.exe" (
    "%LocalAppData%\Python\bin\python.exe" "%~dp0gui_app.py"
    goto :eof
)

where py >nul 2>nul
if not errorlevel 1 (
    py -3 "%~dp0gui_app.py"
    goto :eof
)

where python >nul 2>nul
if not errorlevel 1 (
    python "%~dp0gui_app.py"
    goto :eof
)

echo Khong tim thay Python da cai.
echo Hay cai Python 3.11 tro len, sau do chay lai file nay.
pause
