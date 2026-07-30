from __future__ import annotations

import json
import threading
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from ads_core.meta_service import (
    MetaApiError,
    MetaClient,
    MetaConfig,
    MetaValidationError,
    get_page_client,
    resolve_existing_posts,
    story_id_from_link,
)


DEFAULT_CREATIVE_PREVIEW_CACHE_PATH = (
    Path(__file__).resolve().parent.parent / ".web_state" / "creative_preview_cache.json"
)
CREATIVE_PREVIEW_CACHE_SECONDS = 6 * 60 * 60
MAX_PREVIEW_LINKS = 100
GRAPH_BATCH_SIZE = 50
_CACHE_LOCK = threading.Lock()
_PREVIEW_FIELDS = (
    "id,message,permalink_url,created_time,from{id,name},"
    "attachments.limit(1){media_type,type,url,target,media,"
    "subattachments.limit(10){media_type,type,url,target,media}}"
)


def _is_facebook_link(value: str) -> bool:
    try:
        parsed = urlparse(value)
    except ValueError:
        return False
    host = (parsed.hostname or "").lower()
    return parsed.scheme in {"http", "https"} and (
        host == "facebook.com"
        or host.endswith(".facebook.com")
        or host == "fb.watch"
        or host.endswith(".fb.watch")
    )


def _validate_links(payload: Any) -> list[str]:
    if not isinstance(payload, list) or not payload:
        raise MetaValidationError("Hãy gửi ít nhất một link bài viết để xem creative.")
    if len(payload) > MAX_PREVIEW_LINKS:
        raise MetaValidationError(f"Mỗi lần chỉ xem tối đa {MAX_PREVIEW_LINKS} bài viết.")
    links: list[str] = []
    seen: set[str] = set()
    for raw in payload:
        link = str(raw or "").strip()
        if not link or len(link) > 2048 or not _is_facebook_link(link):
            raise MetaValidationError("Danh sách có link Facebook không hợp lệ.")
        if link not in seen:
            seen.add(link)
            links.append(link)
    return links


def _read_cache(path: Path) -> dict[str, dict[str, Any]]:
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def _write_cache(path: Path, cache: dict[str, dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")
    temporary.replace(path)


def _safe_http_url(value: Any) -> str:
    text = str(value or "").strip()
    try:
        parsed = urlparse(text)
    except ValueError:
        return ""
    return text if parsed.scheme in {"http", "https"} and parsed.netloc else ""


def _first_attachment(post: dict[str, Any]) -> dict[str, Any]:
    attachments = ((post.get("attachments") or {}).get("data") or [])
    if not attachments:
        return {}
    attachment = attachments[0] if isinstance(attachments[0], dict) else {}
    subattachments = ((attachment.get("subattachments") or {}).get("data") or [])
    if subattachments and isinstance(subattachments[0], dict):
        return subattachments[0]
    return attachment


def _ready_preview(link: str, story_id: str, post: dict[str, Any]) -> dict[str, Any]:
    attachment = _first_attachment(post)
    media = attachment.get("media") if isinstance(attachment.get("media"), dict) else {}
    image = media.get("image") if isinstance(media.get("image"), dict) else {}
    author = post.get("from") if isinstance(post.get("from"), dict) else {}
    message = str(post.get("message") or "").strip()
    return {
        "link": link,
        "status": "ready",
        "object_story_id": str(post.get("id") or story_id),
        "page_id": str(author.get("id") or ""),
        "page_name": str(author.get("name") or ""),
        "message": message[:700],
        "media_type": str(attachment.get("media_type") or attachment.get("type") or "post"),
        "thumbnail_url": _safe_http_url(image.get("src")),
        "permalink_url": _safe_http_url(post.get("permalink_url")) or link,
        "created_time": str(post.get("created_time") or ""),
    }


def _unavailable_preview(link: str, reason: str = "") -> dict[str, Any]:
    return {
        "link": link,
        "status": "unavailable",
        "message": "",
        "page_name": "",
        "media_type": "",
        "thumbnail_url": "",
        "permalink_url": link,
        "error": reason or "Không đọc được bài viết bằng quyền Meta hiện tại.",
    }


def _fetch_story_batch(
    api: MetaClient,
    story_ids: list[str],
    links_by_story: dict[str, list[str]],
    previews: dict[str, dict[str, Any]],
) -> None:
    try:
        response = api.get("", ids=",".join(story_ids), fields=_PREVIEW_FIELDS)
    except MetaApiError:
        if len(story_ids) > 1:
            midpoint = len(story_ids) // 2
            _fetch_story_batch(api, story_ids[:midpoint], links_by_story, previews)
            _fetch_story_batch(api, story_ids[midpoint:], links_by_story, previews)
            return
        for link in links_by_story[story_ids[0]]:
            previews[link] = _unavailable_preview(link)
        return
    for story_id in story_ids:
        post = response.get(story_id)
        if not isinstance(post, dict) or post.get("error"):
            for link in links_by_story[story_id]:
                previews[link] = _unavailable_preview(link)
            continue
        for link in links_by_story[story_id]:
            previews[link] = _ready_preview(link, story_id, post)


def get_creative_previews(
    raw_links: Any,
    config: MetaConfig,
    client: MetaClient | None = None,
    *,
    cache_path: Path = DEFAULT_CREATIVE_PREVIEW_CACHE_PATH,
    now: float | None = None,
    refresh: bool = False,
) -> dict[str, Any]:
    links = _validate_links(raw_links)
    if not config.access_token:
        raise MetaValidationError("Backend chưa cấu hình META_ACCESS_TOKEN.")
    api = client or MetaClient(config)
    current_time = time.time() if now is None else now

    with _CACHE_LOCK:
        cache = _read_cache(cache_path)
    previews: dict[str, dict[str, Any]] = {}
    pending: list[str] = []
    for link in links:
        cached = cache.get(link)
        cached_at = cached.get("cached_at") if isinstance(cached, dict) else None
        if (
            not refresh
            and isinstance(cached_at, (int, float))
            and current_time - cached_at < CREATIVE_PREVIEW_CACHE_SECONDS
        ):
            previews[link] = {key: value for key, value in cached.items() if key != "cached_at"}
        else:
            pending.append(link)

    story_by_link = {link: story_id_from_link(link, config.page_id) for link in pending}
    unresolved = [
        link
        for link, story_id in story_by_link.items()
        if not story_id or story_id.startswith("pfbid")
    ]
    resolution_error = ""
    if unresolved:
        try:
            story_by_link.update(resolve_existing_posts(unresolved, config, api, strict=False))
        except (MetaValidationError, MetaApiError) as exc:
            resolution_error = str(exc)

    links_by_story: dict[str, list[str]] = {}
    for link in pending:
        story_id = story_by_link.get(link)
        if story_id:
            links_by_story.setdefault(story_id, []).append(link)
        else:
            previews[link] = _unavailable_preview(link, resolution_error)

    story_ids = list(links_by_story)
    content_api = api
    if story_ids and config.page_id:
        try:
            content_api = get_page_client(config, api)
        except (MetaValidationError, MetaApiError):
            content_api = api
    for offset in range(0, len(story_ids), GRAPH_BATCH_SIZE):
        batch_ids = story_ids[offset : offset + GRAPH_BATCH_SIZE]
        _fetch_story_batch(content_api, batch_ids, links_by_story, previews)

    with _CACHE_LOCK:
        latest_cache = _read_cache(cache_path)
        for link, preview in previews.items():
            if preview.get("status") == "ready":
                latest_cache[link] = {**preview, "cached_at": current_time}
        if latest_cache != cache:
            _write_cache(cache_path, latest_cache)

    ordered = [previews.get(link) or _unavailable_preview(link) for link in links]
    ready_count = sum(item["status"] == "ready" for item in ordered)
    return {
        "previews": ordered,
        "summary": {
            "total": len(ordered),
            "ready": ready_count,
            "unavailable": len(ordered) - ready_count,
        },
    }
