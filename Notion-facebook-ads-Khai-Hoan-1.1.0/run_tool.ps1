$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $projectRoot

$pythonCandidates = @(
    "C:\Users\Admin\AppData\Local\Python\bin\python.exe",
    "C:\Users\Admin\AppData\Local\Python\pythoncore-3.14-64\python.exe"
)

$pythonExe = $pythonCandidates | Where-Object { Test-Path $_ } | Select-Object -First 1

if (-not $pythonExe) {
    Write-Host "Khong tim thay Python da cai." -ForegroundColor Yellow
    Write-Host "Hay chay 'where.exe python' de kiem tra lai." -ForegroundColor Yellow
    exit 1
}

& $pythonExe ".\gui_app.py"
