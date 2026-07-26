# Supabase

Database schema for the dashboard tracking layer.

## Files

- `schema.sql`: dashboard tables, public read policies, and token-gated desktop sync write policies.
- `sync-token.example.sql`: placeholder SQL for setting the private desktop sync token.

## Tables

- `ads_plans`: campaign/ads plan summary rows synced from the desktop tool.
- `ads_plan_items`: row-level ads associated with a plan.
- `ads_exports`: export history and CSV file links.
- `sync_logs`: sync/audit records from desktop, Notion jobs, or future backend workers.
- `sync_settings`: private key/value settings used by RLS helper functions. Do not expose this table to anon users.

## Security Notes

- The frontend uses the publishable key and can only read rows allowed by RLS.
- The current schema allows anonymous reads of operational tables, including `sync_logs`. Restrict these policies before making the dashboard public or multi-tenant.
- The desktop tool can insert/update with the publishable key only when it sends a matching `x-sync-token` header.
- Store the token in `sync_settings` as `desktop_sync_token`, and in the desktop `.env` as `ADS_SYNC_TOKEN`.
- Do not expose `ADS_SYNC_TOKEN`, service role keys, Notion tokens, or Telegram tokens in Vercel public environment variables.

## Next Schema Steps

- Add user/auth policies once login is enabled.
- Add authenticated user/tenant ownership before exposing team data publicly.
- Move desktop writes behind a backend route if the dashboard becomes public or multi-tenant.
