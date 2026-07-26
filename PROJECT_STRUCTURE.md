# Project Structure

This workspace is split into two products that should evolve independently.

## Local Operations Tool

Path: `Notion-facebook-ads-Khai-Hoan-1.1.0/`

Purpose:

- Keep the offline planner/export workflow working.
- Provide both the Windows desktop GUI and the browser-based local planner.
- Create Notion drafts, export Facebook CSV files, and sync summaries to Supabase.

Important areas:

- `gui_app.py`: Tkinter desktop UI.
- `web_app.py` + `web_ui/`: local browser UI and HTTP API.
- `bulk_ads_tool.py`: legacy-compatible API surface for the desktop app.
- `ads_core/`: extracted core modules for safer gradual refactors.
- `config/planner_bundles.json`: offline planner catalog currently in active development.
- `tests/`: Python unit/API tests and Playwright browser tests.

Rule:

- Keep planner validation and export behavior in the local tool.
- Extract small modules only when the behavior can be verified quickly.

## Web Dashboard

Path: `ads-dashboard/`

Purpose:

- Show campaign/ads plan tracking data for the team.
- Read summary data from Supabase.
- Deploy to Vercel.

Important areas:

- `app/components/`: reusable dashboard UI sections.
- `app/lib/`: Supabase API and formatting helpers.
- `app/types/`: shared TypeScript data shapes.
- `supabase/schema.sql`: database tables for dashboard tracking.

Rule:

- Dashboard should not own planner logic yet.
- It reads campaign summary and export history first.
- Planner migration to server happens only after desktop sync and dashboard tracking are stable.

## Current Data Flow

```text
Desktop Tool
  -> creates planner and Notion drafts locally
  -> exports Facebook CSV
  -> syncs plans, items, exports, and logs to Supabase

Supabase
  -> stores ads_plans, ads_plan_items, ads_exports, and sync_logs

Web Dashboard
  -> reads Supabase and shows tracking view
```

## Future Data Flow

```text
Hosted Web App
  -> may own planner and validation after authentication is added
  -> writes Supabase
  -> exports Facebook CSV
  -> syncs overview to Notion

Desktop Tool
  -> remains admin/backup/local export
```
