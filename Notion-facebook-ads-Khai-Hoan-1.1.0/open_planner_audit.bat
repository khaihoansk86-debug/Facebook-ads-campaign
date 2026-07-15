@echo off
setlocal
cd /d "%~dp0"

set "PYTHON_BIN=C:\Users\Admin\AppData\Local\Python\bin\python.exe"
if exist "%PYTHON_BIN%" (
    "%PYTHON_BIN%" "%~dp0planner_audit_tool.py" --open
    goto :done
)

set "PYTHON_BIN=C:\Users\Admin\AppData\Local\Python\pythoncore-3.14-64\python.exe"
if exist "%PYTHON_BIN%" (
    "%PYTHON_BIN%" "%~dp0planner_audit_tool.py" --open
    goto :done
)

python "%~dp0planner_audit_tool.py" --open

:done
if errorlevel 1 (
    echo.
    echo Khong tao duoc Planner Audit Report.
    pause
)
