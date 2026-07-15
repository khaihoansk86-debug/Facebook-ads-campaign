from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from pathlib import Path

from ads_core.settings import NOTION_VERSION


def load_env(path):
    env_path = Path(path)
    if not env_path.exists():
        return
    for raw_line in env_path.read_text(encoding="utf-8-sig").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip().lstrip("\ufeff")
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


def notion_request(method, path, payload=None, notion_version=NOTION_VERSION):
    token = os.environ.get("NOTION_TOKEN")
    if not token:
        raise RuntimeError("Thiếu NOTION_TOKEN trong biến môi trường hoặc file .env")
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        f"https://api.notion.com/v1{path}",
        data=data,
        method=method,
        headers={
            "Authorization": f"Bearer {token}",
            "Notion-Version": notion_version,
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Notion API lỗi {exc.code}: {detail}") from exc


def plain_text(blocks):
    return "".join(item.get("plain_text", "") for item in blocks or [])


def property_value(prop):
    if not prop:
        return ""
    prop_type = prop.get("type")
    value = prop.get(prop_type)
    if prop_type in ("title", "rich_text"):
        return plain_text(value)
    if prop_type == "select":
        return "" if value is None else value.get("name", "")
    if prop_type == "multi_select":
        return ", ".join(item.get("name", "") for item in value or [])
    if prop_type == "checkbox":
        return bool(value)
    if prop_type == "number":
        return "" if value is None else str(value).replace(".", ",")
    if prop_type in ("url", "email", "phone_number"):
        return value or ""
    if prop_type == "date":
        return "" if value is None else value.get("start", "")
    if prop_type == "status":
        return "" if value is None else value.get("name", "")
    return ""


def property_payload(prop, value):
    prop_type = prop.get("type")
    if prop_type == "title":
        return {"title": [{"type": "text", "text": {"content": str(value)}}]}
    if prop_type == "rich_text":
        return {"rich_text": [{"type": "text", "text": {"content": str(value)}}]}
    if prop_type == "url":
        return {"url": str(value)}
    if prop_type == "number":
        if value in ("", None):
            return {"number": None}
        return {"number": float(str(value).replace(",", "."))}
    if prop_type == "checkbox":
        return {"checkbox": bool(value)}
    if prop_type == "select":
        return {"select": {"name": str(value)}}
    if prop_type == "status":
        return {"status": {"name": str(value)}}
    if prop_type == "date":
        return {"date": {"start": str(value)}} if value else {"date": None}
    return None
