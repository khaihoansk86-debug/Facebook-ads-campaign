# Khai Hoan Ads Dashboard

Internal dashboard for tracking ads plans synced from the desktop tool.

## 1. Create Supabase Tables

Open Supabase SQL Editor and run:

```sql
-- ads-dashboard/supabase/schema.sql
```

The first version creates:

- `ads_plans`
- `ads_exports`
- read-only RLS policies for dashboard access

## 2. Configure Local Env

Create `.env.local` from `.env.local.example` and fill the project URL:

```env
NEXT_PUBLIC_SUPABASE_URL=https://kuelttmrhdkajclaaths.supabase.co
NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY=sb_publishable_M8diN1bi6qdzCDZVVWQc1Q_Bmnme-Zw
```

Keep the service role key out of the frontend. It will only be used by the desktop sync tool or a backend route.

## 3. Run Dashboard

```powershell
npm install
npm run dev
```

## 4. Deploy To Vercel

Create a Vercel project from this folder and add:

```env
NEXT_PUBLIC_SUPABASE_URL=
NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY=
```

After deploy, the dashboard reads campaign summaries from `ads_plans`.

## 5. Module Structure

- `app/components`: dashboard UI sections.
- `app/lib`: Supabase REST access and helpers.
- `app/types`: shared TypeScript data shapes.
- `supabase`: SQL schema and database notes.

Keep planner logic in the desktop tool until the tracking dashboard and sync workflow are stable.
