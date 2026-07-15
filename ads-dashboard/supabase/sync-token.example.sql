-- Run schema.sql first, then set the desktop sync token.
-- Replace the placeholder with ADS_SYNC_TOKEN from the desktop .env file.

insert into public.sync_settings(key, value)
values ('desktop_sync_token', 'PASTE_ADS_SYNC_TOKEN_HERE')
on conflict (key)
do update set
  value = excluded.value,
  updated_at = now();
