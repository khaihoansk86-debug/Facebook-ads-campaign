$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $projectRoot

$pythonCore = Get-ChildItem (Join-Path $env:LocalAppData "Python\pythoncore-*\python.exe") -ErrorAction SilentlyContinue |
  Sort-Object FullName -Descending |
  Select-Object -First 1
$localPython = if ($pythonCore) { $pythonCore.FullName } else { Join-Path $env:LocalAppData "Python\bin\python.exe" }
if (Test-Path $localPython) {
  $pythonExe = $localPython
  $pythonPrefix = @()
} elseif (Get-Command py -ErrorAction SilentlyContinue) {
  $pythonExe = "py"
  $pythonPrefix = @("-3")
} elseif (Get-Command python -ErrorAction SilentlyContinue) {
  $pythonExe = "python"
  $pythonPrefix = @()
} else {
  throw "Khong tim thay Python. Hay cai Python 3.11 tro len."
}

& $pythonExe @pythonPrefix -c "import PyInstaller, customtkinter"
if ($LASTEXITCODE -ne 0) {
  throw "Thieu dependency build. Hay chay: python -m pip install -r requirements.txt"
}

& $pythonExe @pythonPrefix -m PyInstaller `
  --onefile `
  --windowed `
  --name "NotionFacebookAdsTool" `
  --icon "assets/app_icon.ico" `
  --collect-all "customtkinter" `
  --add-data "assets;assets" `
  --add-data "config;config" `
  --add-data "sample;sample" `
  "gui_app.py"

if ($LASTEXITCODE -ne 0) {
  throw "PyInstaller build that bai."
}

$outputPath = Join-Path $projectRoot "dist\NotionFacebookAdsTool.exe"
if (-not (Test-Path $outputPath)) {
  throw "Build hoan tat nhung khong tim thay file $outputPath."
}

Write-Host "EXE da tao tai: dist\\NotionFacebookAdsTool.exe"
