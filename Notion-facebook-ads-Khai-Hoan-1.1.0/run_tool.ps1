$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $projectRoot

$pythonCore = Get-ChildItem (Join-Path $env:LocalAppData "Python\pythoncore-*\python.exe") -ErrorAction SilentlyContinue |
    Sort-Object FullName -Descending |
    Select-Object -First 1
$localPython = if ($pythonCore) { $pythonCore.FullName } else { Join-Path $env:LocalAppData "Python\bin\python.exe" }
if (Test-Path $localPython) {
    & $localPython ".\gui_app.py"
    exit $LASTEXITCODE
}

if (Get-Command py -ErrorAction SilentlyContinue) {
    & py -3 ".\gui_app.py"
    exit $LASTEXITCODE
}

if (Get-Command python -ErrorAction SilentlyContinue) {
    & python ".\gui_app.py"
    exit $LASTEXITCODE
}

Write-Host "Khong tim thay Python. Hay cai Python 3.11 tro len." -ForegroundColor Yellow
exit 1
