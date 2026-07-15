$ErrorActionPreference = "Stop"
python -m pip install pyinstaller
python -m PyInstaller `
  --onefile `
  --windowed `
  --name "NotionFacebookAdsTool" `
  --add-data "bulk_ads_tool.py;." `
  "gui_app.py"
Write-Host "EXE da tao tai: dist\\NotionFacebookAdsTool.exe"
