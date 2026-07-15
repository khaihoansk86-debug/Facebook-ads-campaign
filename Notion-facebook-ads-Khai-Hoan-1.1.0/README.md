# Notion -> Facebook Ads Khai Hoan

Desktop tool for preparing Facebook Ads Manager bulk import files from a Notion database.

The workflow is designed for an ads team where a manager reviews Facebook post links in Notion, selects campaign/ad set settings, then exports one Facebook-compatible CSV file for bulk import.

## Features

- Create Notion draft rows from one or many Facebook post/reel links.
- Resolve Facebook `/posts/pfbid...` links into numeric `Story ID` when possible, so Ads Manager selects the correct existing post.
- Store campaign, ad set, budget, bid, demographic, placement, device and audience settings in Notion.
- Provide ready-to-use dropdowns for ad set names and audience presets.
- Export multiple approved Notion rows into one CSV file.
- Clone the original Facebook Ads Manager bulk CSV template to preserve Meta's expected columns and formatting.
- Mark exported Notion rows as done to avoid duplicate exports.
- Optional Supabase sync after export for the web dashboard campaign tracker.
- Optional Telegram notification after export.
- Portable Windows GUI built with Python/Tkinter and PyInstaller.

## Workflow

1. Paste one or many Facebook links into the desktop app.
2. The app creates draft rows in Notion with status `In progress`.
3. The manager reviews each row in Notion and chooses:
   - `Ten nhom QC`
   - `Mau doi tuong`
   - budget, bid, placement, page, CTA and other settings if needed.
4. When ready, set status to `Ready`, `To-do`, `Not started`, or enable export for `In progress` in the app.
5. Click `Xuat CSV`.
6. The app exports one CSV file in `exports/`.
7. If Supabase is configured, the app syncs a campaign/export summary to the web dashboard.
8. Import the CSV into Facebook Ads Manager.

## Current Notion Defaults

The included setup is tuned for Khai Hoan's Facebook Ads workflow:

- Page/database: `Facebook Ads Manager - Khai Hoan`
- Data Source ID: `670be938-5dd2-497a-bd32-a9a5401c4789`
- Parent Page ID: `0d89661f16ee43fcaa7abad46058b9bc`

These IDs are defaults only. You can replace them in `.env` or in the app's `Cau hinh` tab.

## Ad Set Dropdowns

The `Ten nhom QC` Notion column is configured as a dropdown with these options:

- `T2 Tin nhan | Da tuong tac Page`
- `T3 Tin nhan | Da nhan tin page`
- `T1 Video/ThruPlay | Khach lanh Phan Thiet`
- `Tang tuong tac | Khach lanh Phan Thiet`
- `Tang tuong tac | Da tuong tac page`
- `Khach lanh Phan Thiet`

Use the same campaign name and ad set name across multiple rows to group many ads into the same campaign/ad set in Facebook Bulk Import.

## Files

```text
bulk_ads_tool.py              Core Notion, Facebook CSV and export logic
gui_app.py                    Desktop GUI
sample/facebook_ads_template.csv
                              Facebook Ads Manager bulk import template
notion_template_columns.csv   Human-readable Notion column reference
config/custom_mapping.example.json
                              Optional Notion-to-Facebook column override mapping
.env.example                  Environment variable template
build_exe.ps1                 PyInstaller build helper
INSTALL.md                    Portable install notes
```

## Requirements

- Python 3.11+
- Windows for the packaged GUI build
- A Notion integration token with access to the target database/page
- Facebook Ads Manager bulk import CSV template

Install Python dependencies:

```powershell
pip install -r requirements.txt
```

## Configuration

Copy `.env.example` to `.env`:

```powershell
Copy-Item .env.example .env
```

Then edit `.env`:

```env
NOTION_TOKEN=ntn_xxx
NOTION_DATA_SOURCE_ID=670be938-5dd2-497a-bd32-a9a5401c4789
NOTION_DATABASE_ID=670be938-5dd2-497a-bd32-a9a5401c4789
PARENT_PAGE_ID=0d89661f16ee43fcaa7abad46058b9bc
SAMPLE_CSV=sample/facebook_ads_template.csv
TEMPLATE_ROW_INDEX=0
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=
SUPABASE_URL=https://kuelttmrhdkajclaaths.supabase.co
SUPABASE_PUBLISHABLE_KEY=
ADS_SYNC_TOKEN=
# Optional fallback only if Supabase accepts service_role over REST.
SUPABASE_SECRET_KEY=
```

Never commit `.env`. It contains private tokens.

The preferred desktop sync flow uses `SUPABASE_PUBLISHABLE_KEY` plus `ADS_SYNC_TOKEN`. The token is checked by Supabase RLS policies through the `x-sync-token` header. Do not put `ADS_SYNC_TOKEN`, `SUPABASE_SECRET_KEY`, Notion tokens, or Telegram tokens in `ads-dashboard`, Vercel public variables, or frontend code.

## Run The GUI

```powershell
python gui_app.py
```

Main tabs:

- `Nhap link bai`: paste Facebook links and create draft rows in Notion.
- `Xuat CSV`: export approved rows to one CSV file.
- `Cau hinh`: edit Notion, template CSV and Telegram settings.
- `Notion mau`: create or open the Notion template database.
- `Nhat ky`: inspect runtime logs.

## Command Line Export

Export ready rows:

```powershell
python bulk_ads_tool.py export --mark-exported
```

Export without marking rows as exported:

```powershell
python bulk_ads_tool.py export
```

The exported file is written to:

```text
exports/facebook_bulk_YYYYMMDD_HHMMSS.csv
```

The CSV is UTF-16 with tab delimiters, matching Facebook Ads Manager bulk import format.

When Supabase sync is configured, each export also upserts one `ads_plans` record, one `ads_exports` record, and a `sync_logs` success/error entry. If Supabase fails, the CSV export still completes and the warning is printed/logged.

## Build Windows EXE

Install build dependencies:

```powershell
pip install -r requirements.txt
```

Build:

```powershell
.\build_exe.ps1
```

Or run PyInstaller directly:

```powershell
python -m PyInstaller --onefile --windowed --name "Notion Facebook Ads Khai Hoan" --icon ".\assets\app_icon.ico" "gui_app.py"
```

The EXE is generated under `dist/`.

## Security Notes

- Do not commit `.env`, `.sync_state.json`, `exports/`, `dist/` or `build/`.
- Do not hardcode Notion tokens, Telegram tokens or Facebook account secrets.
- The sample CSV may contain campaign/template values; review before publishing to a public repository if your ad account setup is sensitive.

## Known Limitations

- Facebook post metadata resolution depends on Facebook's public page HTML structure and can break if Meta changes markup.
- Some private or restricted Facebook posts may not expose enough data for automatic `Story ID` resolution.
- Facebook Ads Manager remains the final validator for bulk import compatibility.

## License

Private/internal project unless a license is added.
