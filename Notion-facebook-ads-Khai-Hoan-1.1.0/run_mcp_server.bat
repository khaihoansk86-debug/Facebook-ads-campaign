@echo off
setlocal
cd /d "%~dp0"

set "PYTHON_BIN="
for /d %%D in ("%LocalAppData%\Python\pythoncore-*") do set "PYTHON_BIN=%%~fD\python.exe"
if defined PYTHON_BIN if exist "%PYTHON_BIN%" (
  "%PYTHON_BIN%" mcp_server.py
  goto :done
)

if exist "%LocalAppData%\Python\bin\python.exe" (
  "%LocalAppData%\Python\bin\python.exe" mcp_server.py
  goto :done
)

where py >nul 2>nul
if not errorlevel 1 (
  py -3 mcp_server.py
  goto :done
)

where python >nul 2>nul
if not errorlevel 1 (
  python mcp_server.py
  goto :done
)

echo Khong tim thay Python. Hay cai Python 3.11 tro len tren may server.
pause
exit /b 1

:done
if errorlevel 1 (
  echo.
  echo MCP server da dung do co loi. Hay chay: python mcp_server.py --self-test
  pause
)
