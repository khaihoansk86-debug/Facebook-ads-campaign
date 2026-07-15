create table if not exists public.ads_plans (
  id uuid primary key default gen_random_uuid(),
  external_id text unique,
  name text not null,
  status text not null default 'draft',
  objective text,
  owner_name text,
  ads_count integer not null default 0,
  adsets_count integer not null default 0,
  audiences_count integer not null default 0,
  budget_total numeric,
  source text not null default 'desktop',
  source_payload jsonb not null default '{}'::jsonb,
  notion_url text,
  latest_csv_url text,
  last_exported_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists ads_plans_status_idx on public.ads_plans(status);
create index if not exists ads_plans_updated_at_idx on public.ads_plans(updated_at desc);
create index if not exists ads_plans_external_id_idx on public.ads_plans(external_id);

alter table public.ads_plans enable row level security;

drop policy if exists "Allow public read ads plans" on public.ads_plans;
create policy "Allow public read ads plans"
on public.ads_plans
for select
to anon, authenticated
using (true);

create table if not exists public.ads_exports (
  id uuid primary key default gen_random_uuid(),
  plan_id uuid references public.ads_plans(id) on delete cascade,
  external_id text unique,
  file_name text not null,
  file_url text,
  rows_count integer not null default 0,
  exported_by text,
  source_payload jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

alter table public.ads_exports enable row level security;

drop policy if exists "Allow public read ads exports" on public.ads_exports;
create policy "Allow public read ads exports"
on public.ads_exports
for select
to anon, authenticated
using (true);

create table if not exists public.sync_logs (
  id uuid primary key default gen_random_uuid(),
  source text not null default 'desktop',
  entity_type text not null,
  entity_external_id text,
  status text not null,
  message text,
  payload jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create index if not exists sync_logs_created_at_idx on public.sync_logs(created_at desc);
create index if not exists sync_logs_entity_idx on public.sync_logs(entity_type, entity_external_id);

alter table public.sync_logs enable row level security;

drop policy if exists "Allow public read sync logs" on public.sync_logs;
create policy "Allow public read sync logs"
on public.sync_logs
for select
to anon, authenticated
using (true);

create table if not exists public.sync_settings (
  key text primary key,
  value text not null,
  updated_at timestamptz not null default now()
);

alter table public.sync_settings enable row level security;

create or replace function public.request_header(header_name text)
returns text
language plpgsql
stable
as $$
declare
  headers jsonb;
begin
  headers := nullif(current_setting('request.headers', true), '')::jsonb;
  return headers ->> lower(header_name);
exception
  when others then
    return null;
end;
$$;

create or replace function public.is_valid_desktop_sync()
returns boolean
language sql
stable
security definer
set search_path = public
as $$
  select exists (
    select 1
    from public.sync_settings
    where key = 'desktop_sync_token'
      and value = public.request_header('x-sync-token')
  );
$$;

grant execute on function public.request_header(text) to anon, authenticated;
grant execute on function public.is_valid_desktop_sync() to anon, authenticated;

drop policy if exists "Allow desktop sync insert ads plans" on public.ads_plans;
create policy "Allow desktop sync insert ads plans"
on public.ads_plans
for insert
to anon, authenticated
with check (public.is_valid_desktop_sync());

drop policy if exists "Allow desktop sync update ads plans" on public.ads_plans;
create policy "Allow desktop sync update ads plans"
on public.ads_plans
for update
to anon, authenticated
using (public.is_valid_desktop_sync())
with check (public.is_valid_desktop_sync());

drop policy if exists "Allow desktop sync insert ads exports" on public.ads_exports;
create policy "Allow desktop sync insert ads exports"
on public.ads_exports
for insert
to anon, authenticated
with check (public.is_valid_desktop_sync());

drop policy if exists "Allow desktop sync update ads exports" on public.ads_exports;
create policy "Allow desktop sync update ads exports"
on public.ads_exports
for update
to anon, authenticated
using (public.is_valid_desktop_sync())
with check (public.is_valid_desktop_sync());

drop policy if exists "Allow desktop sync insert sync logs" on public.sync_logs;
create policy "Allow desktop sync insert sync logs"
on public.sync_logs
for insert
to anon, authenticated
with check (public.is_valid_desktop_sync());

create or replace function public.set_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

drop trigger if exists set_ads_plans_updated_at on public.ads_plans;
create trigger set_ads_plans_updated_at
before update on public.ads_plans
for each row
execute function public.set_updated_at();
