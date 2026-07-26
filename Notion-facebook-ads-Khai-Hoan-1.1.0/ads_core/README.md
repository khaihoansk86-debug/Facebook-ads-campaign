# ads_core

Small core modules extracted from `bulk_ads_tool.py`.

The desktop app still imports through `bulk_ads_tool.py` for backwards compatibility. Keep that public surface stable while moving implementation details here in small, verified steps.

## Modules

- `settings.py`: shared constants and portable default paths.
- `notion_api.py`: Notion HTTP calls, `.env` loading, Notion property conversion.
- `facebook_csv.py`: read/write Facebook bulk CSV files.
- `planner_catalog.py`: load/save planner bundle catalog.
- `mapping.py`: Notion-to-Facebook column mapping and value aliases.
- `planner_service.py`: planner request validation and preview expansion.
- `draft_service.py`: idempotent Notion draft orchestration backed by a local ledger.
- `export_service.py`: candidate listing and selective Facebook CSV export.
- `preset_service.py`: validated planner preset creation and updates.
- `supabase_sync.py`: low-level Supabase REST sync helpers. Preferred authentication is a publishable key plus `ADS_SYNC_TOKEN`; a secret key remains a backend-only fallback.

## Rules

- Do not move active planner behavior wholesale while the offline planner is still being built.
- Keep pure data and I/O helpers here; keep GUI-specific code in `gui_app.py`.
- After each extraction, run the Python unit suite and the Playwright local web suite.
- Preserve old imports from `bulk_ads_tool.py` unless every caller has been migrated.

## Next Candidates

- `notion_schema.py`: `NOTION_PROPERTIES`, `DRAFT_DEFAULT_VALUES`, legacy audience defaults.
- `facebook_links.py`: Facebook URL parsing and metadata resolution.
- `notion_schema.py`: Notion schema validation and property definitions.
- `facebook_links.py`: Facebook URL parsing and metadata resolution.
- `supabase_export_service.py`: move summary payload construction out of `bulk_ads_tool.py`.
