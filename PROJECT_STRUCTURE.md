# Project Structure

This workspace is split into two products that should evolve independently.

## Desktop Tool

Path: `Notion-facebook-ads-Khai-Hoan-1.1.0/`

Purpose:

- Keep the current offline planner/export workflow working.
- Continue developing planner bundles, Notion draft creation, and Facebook CSV export.
- Later, add a sync client that pushes summary data to Supabase.

Important areas:

- `gui_app.py`: Tkinter desktop UI.
- `bulk_ads_tool.py`: legacy-compatible API surface for the desktop app.
- `ads_core/`: extracted core modules for safer gradual refactors.
- `config/planner_bundles.json`: offline planner catalog currently in active development.

Rule:

- Do not move or rewrite planner offline logic while it is still being stabilized.
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
  -> creates planner/export locally
  -> later syncs summary to Supabase

Supabase
  -> stores ads_plans and ads_exports

Web Dashboard
  -> reads Supabase and shows tracking view
```

## Future Data Flow

```text
Web App
  -> owns planner and validation
  -> writes Supabase
  -> exports Facebook CSV
  -> syncs overview to Notion

Desktop Tool
  -> remains admin/backup/local export
```
