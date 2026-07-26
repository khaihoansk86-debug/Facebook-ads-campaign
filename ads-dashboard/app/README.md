# app

Next.js App Router dashboard for campaign tracking.

This app reads summary and row-level ad data from Supabase. It does not own planner logic; planner selection and CSV export live in the local operations tool.

## Folders

- `components/`: reusable UI sections for the dashboard.
- `lib/`: Supabase REST access and formatting helpers.
- `types/`: shared TypeScript data shapes.
- `page.tsx`: page composition only; keep heavy logic out of this file.
- `styles.css`: global dashboard styling.

## Rules

- Keep Supabase `service_role` out of all `NEXT_PUBLIC_*` variables.
- Put reusable UI in `components/`, not directly in `page.tsx`.
- Put API/data fetching helpers in `lib/`.
- Add fields to `types/ads.ts` when `supabase/schema.sql` changes.
- Keep planner migration out of this app until desktop sync and campaign tracking are stable.
