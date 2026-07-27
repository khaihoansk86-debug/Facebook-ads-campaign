# Notion -> Facebook Ads Khai Hoan

Local operations tool for preparing Facebook Ads Manager bulk import files from a Notion database. It includes a Windows desktop GUI and a browser-based local planner.

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
- Browser planner with preview, reusable presets, selective export, and safe retry protection.
- Portable Windows GUI built with Python/Tkinter and PyInstaller.

## Workflow

1. Paste one or many Facebook links into the desktop app or local web planner.
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

## Notion Configuration

The repository does not contain a default Notion token or database ID. Copy `.env.example` to `.env`, then provide the IDs for the workspace being used. Existing installations keep their current values in their ignored `.env` file.

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
web_app.py                    Local HTTP API and static web server
web_ui/                       Browser planner UI
ads_core/planner_service.py   Planner validation and preview
ads_core/draft_service.py     Safe Notion draft creation and retry ledger
ads_core/export_service.py    Selective Facebook CSV export
ads_core/preset_service.py    Audience, budget and placement preset management
tests/                        Python and Playwright test suites
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
NOTION_DATA_SOURCE_ID=your_notion_data_source_id
NOTION_DATABASE_ID=
PARENT_PAGE_ID=
SAMPLE_CSV=sample/facebook_ads_template.csv
TEMPLATE_ROW_INDEX=0
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=
SUPABASE_URL=https://your-project-ref.supabase.co
SUPABASE_PUBLISHABLE_KEY=
ADS_SYNC_TOKEN=
# Optional fallback only if Supabase accepts service_role over REST.
SUPABASE_SECRET_KEY=
```

Never commit `.env`. It contains private tokens.

The preferred desktop sync flow uses `SUPABASE_PUBLISHABLE_KEY` plus `ADS_SYNC_TOKEN`. The token is checked by Supabase RLS policies through the `x-sync-token` header. Do not put `ADS_SYNC_TOKEN`, `SUPABASE_SECRET_KEY`, Notion tokens, or Telegram tokens in `ads-dashboard`, Vercel public variables, or frontend code.

## Run The GUI

```powershell
.\run_tool.ps1
```

Main tabs:

- `Nhap link bai`: paste Facebook links and create draft rows in Notion.
- `Xuat CSV`: export approved rows to one CSV file.
- `Cau hinh`: edit Notion, template CSV and Telegram settings.
- `Notion mau`: create or open the Notion template database.
- `Nhat ky`: inspect runtime logs.

## Run The Local Web Planner

```powershell
.\run_web.bat
```

Or:

```powershell
python web_app.py
```

The server binds to `127.0.0.1:8000` by default. Plans in progress are kept in browser local storage.

The Planner now uses Meta Marketing API as the primary publish flow:

1. `Xem trước` validates the ad account, currency, existing-post story IDs, and mapped source ad sets without writing.
2. `Tạo bản nháp PAUSED trên Meta` creates one campaign and one ad set per Planner flow, then one ad per Facebook link.
3. Campaigns, ad sets, and ads are always created as `PAUSED`.
4. `.web_state/meta_publish_ledger.json` stores every Meta object ID after each successful step, so a retry resumes instead of creating duplicates.
5. `CSV dự phòng` keeps the old Notion review/export workflow available during migration.

Configure Meta only in the backend `.env`:

```env
META_ACCESS_TOKEN=
META_API_VERSION=v25.0
META_AD_ACCOUNT_ID=act_123456789
META_PAGE_ID=123456789
META_TEST_MODE=true
META_ADSET_TEMPLATE_MAP={"ENG_POST_COLD":"123456789"}
META_ALLOW_DEFAULT_TEMPLATE=false
```

Each Planner ad-set bundle must be mapped to a proven Meta source ad set before it can publish. This deliberately blocks an unsupported bundle instead of silently copying the wrong optimization, promoted object, targeting, or placement settings. Use a System User token for the fixed backend; short-lived Graph API Explorer tokens are for testing only. Never expose `META_ACCESS_TOKEN` in Vercel or browser code.

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

When Supabase sync is configured, each export also upserts `ads_plans`, `ads_plan_items`, `ads_exports`, and a `sync_logs` success/error entry. If Supabase fails, the CSV export still completes and the warning is printed/logged.

## Build Windows EXE

Install build dependencies:

```powershell
pip install -r requirements.txt
```

Build:

```powershell
.\build_exe.ps1
```

The build helper verifies the installed requirements and bundles the CustomTkinter resources, application assets, planner catalog, and sample CSV. The EXE is generated under `dist/`.

## Verify

```powershell
python -m unittest discover -s tests -p "test_*.py"
npm install
npm run test:e2e
```

## Security Notes

- Do not commit `.env`, `.sync_state.json`, `exports/`, `dist/` or `build/`.
- Do not hardcode Notion tokens, Telegram tokens or Facebook account secrets.
- The sample CSV may contain campaign/template values; review before publishing to a public repository if your ad account setup is sensitive.

## Known Limitations

- Standard Page post URLs can be converted directly to `page_id_post_id`. Short links, share links, and some Reel URLs need `META_PAGE_ID` plus Page read access so the backend can resolve them.
- Only Planner ad-set codes present in `META_ADSET_TEMPLATE_MAP` can publish. Add mappings gradually after each source ad set is regression-tested.
- The current local HTTP server has no employee authentication and must not be exposed directly to the public internet. Put authentication and HTTPS in front of it before office-wide deployment.
- CSV export remains the fallback while the Meta API mappings are expanded.

## License

Private/internal project unless a license is added.
