# ads_core

Small core modules extracted from `bulk_ads_tool.py`.

The desktop app still imports through `bulk_ads_tool.py` for backwards compatibility. Keep that public surface stable while moving implementation details here in small, verified steps.

## Modules

- `settings.py`: shared constants and default IDs.
- `notion_api.py`: Notion HTTP calls, `.env` loading, Notion property conversion.
- `facebook_csv.py`: read/write Facebook bulk CSV files.
- `planner_catalog.py`: load/save planner bundle catalog.
- `mapping.py`: Notion-to-Facebook column mapping and value aliases.
- `supabase_sync.py`: low-level Supabase REST sync helpers for dashboard tracking. It uses `SUPABASE_SECRET_KEY` on desktop/backend only.

## Rules

- Do not move active planner behavior wholesale while the offline planner is still being built.
- Keep pure data and I/O helpers here; keep GUI-specific code in `gui_app.py`.
- After each extraction, run `py_compile`, `planner_audit_tool.py`, and `scratch/validate_planner_flow.mjs`.
- Preserve old imports from `bulk_ads_tool.py` unless every caller has been migrated.

## Next Candidates

- `notion_schema.py`: `NOTION_PROPERTIES`, `DRAFT_DEFAULT_VALUES`, legacy audience defaults.
- `facebook_links.py`: Facebook URL parsing and metadata resolution.
- `export_service.py`: query Notion, build rows, write CSV, mark exported.
- `export_service.py`: move the export orchestration and Supabase summary payload builder out of `bulk_ads_tool.py`.
