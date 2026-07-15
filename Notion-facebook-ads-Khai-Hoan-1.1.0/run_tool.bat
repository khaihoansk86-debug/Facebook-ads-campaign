@echo off
setlocal
cd /d "%~dp0"

set "PYTHON_BIN=C:\Users\Admin\AppData\Local\Python\bin\python.exe"
if exist "%PYTHON_BIN%" (
    "%PYTHON_BIN%" "%~dp0gui_app.py"
    goto :eof
)

set "PYTHON_BIN=C:\Users\Admin\AppData\Local\Python\pythoncore-3.14-64\python.exe"
if exist "%PYTHON_BIN%" (
    "%PYTHON_BIN%" "%~dp0gui_app.py"
    goto :eof
)

echo Khong tim thay Python da cai.
echo Hay mo PowerShell va chay:
echo   where.exe python
pause
