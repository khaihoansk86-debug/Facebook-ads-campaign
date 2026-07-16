from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from urllib.parse import urlencode


def _supabase_secret_key():
    return os.environ.get("SUPABASE_SECRET_KEY") or os.environ.get("SUPABASE_SERVICE_ROLE_KEY")


def _supabase_publishable_key():
    return os.environ.get("SUPABASE_PUBLISHABLE_KEY") or os.environ.get("NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY")


def _supabase_api_key():
    return _supabase_publishable_key() or _supabase_secret_key()


def is_supabase_sync_configured():
    has_secret_auth = bool(_supabase_secret_key())
    has_token_auth = bool(_supabase_publishable_key() and os.environ.get("ADS_SYNC_TOKEN"))
    return bool(os.environ.get("SUPABASE_URL") and (has_secret_auth or has_token_auth))


def supabase_request(method, path, payload=None, prefer=None, query=None):
    supabase_url = os.environ.get("SUPABASE_URL")
    api_key = _supabase_api_key()
    if not supabase_url or not api_key:
        raise RuntimeError("Thiếu SUPABASE_URL và key Supabase để sync dashboard.")

    data = None if payload is None else json.dumps(payload).encode("utf-8")
    headers = {
        "apikey": api_key,
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    sync_token = os.environ.get("ADS_SYNC_TOKEN")
    if sync_token and _supabase_publishable_key():
        headers["x-sync-token"] = sync_token
    if prefer:
        headers["Prefer"] = prefer

    query_string = f"?{urlencode(query)}" if query else ""
    request = urllib.request.Request(
        f"{supabase_url.rstrip('/')}/rest/v1/{path.lstrip('/')}{query_string}",
        data=data,
        method=method,
        headers=headers,
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            body = response.read().decode("utf-8")
            return json.loads(body) if body else None
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Supabase API lỗi {exc.code}: {detail}") from exc


def upsert_ads_plan(plan):
    return supabase_request(
        "POST",
        "ads_plans",
        payload=plan,
        prefer="resolution=merge-duplicates,return=representation",
        query={"on_conflict": "external_id"},
    )


def insert_ads_export(export_record):
    return supabase_request(
        "POST",
        "ads_exports",
        payload=export_record,
        prefer="resolution=merge-duplicates,return=representation",
        query={"on_conflict": "external_id"},
    )


def upsert_ads_plan_items(items):
    if not items:
        return None
    return supabase_request(
        "POST",
        "ads_plan_items",
        payload=items,
        prefer="resolution=merge-duplicates,return=representation",
        query={"on_conflict": "external_id"},
    )


def insert_sync_log(log_record):
    return supabase_request(
        "POST",
        "sync_logs",
        payload=log_record,
        prefer="return=minimal",
    )
