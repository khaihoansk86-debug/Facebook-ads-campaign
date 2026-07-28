from __future__ import annotations

import hashlib
import json
import threading
import uuid
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from ads_core.planner_service import preview_plan


DEFAULT_REVIEW_STORE_PATH = Path(__file__).resolve().parent.parent / ".web_state" / "planner_reviews.json"
REVIEW_STATUSES = {"PENDING_REVIEW", "APPROVED", "REJECTED", "PUBLISHING", "META_CREATED"}
_STORE_LOCK = threading.RLock()


class ReviewValidationError(ValueError):
    pass


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _snapshot(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "links": deepcopy(payload.get("links") or []),
        "flows": deepcopy(payload.get("flows") or []),
        "ad_name": str(payload.get("ad_name") or "").strip(),
    }


def _payload_hash(payload: dict[str, Any]) -> str:
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _build_tree(plan: dict[str, Any]) -> list[dict[str, Any]]:
    campaigns: list[dict[str, Any]] = []
    by_campaign: dict[str, dict[str, Any]] = {}
    for flow in plan["flows"]:
        campaign_code = flow["campaign_code"]
        campaign = by_campaign.get(campaign_code)
        if campaign is None:
            campaign = {
                "code": campaign_code,
                "name": flow["campaign_name"],
                "adsets": [],
            }
            by_campaign[campaign_code] = campaign
            campaigns.append(campaign)
        campaign["adsets"].append(
            {
                "position": flow["position"],
                "code": flow["adset_code"],
                "name": flow["adset_name"],
                "conversion_location": flow["conversion_location"],
                "performance_goal": flow["performance_goal"],
                "audiences": flow["audiences"],
                "dataset": flow["dataset"],
                "budget": flow["budget"],
                "budget_type": flow["budget_type"],
                "custom_budget_values": flow["custom_budget_values"],
                "start_time": flow["start_time"],
                "end_time": flow["end_time"],
                "placement": flow["placement"],
                "ads": [
                    {
                        "position": index,
                        "name": f"Bài {index}",
                        "link": link,
                        "creative_mode": flow["creative_mode"],
                    }
                    for index, link in enumerate(flow["links"], start=1)
                ],
            }
        )
    return campaigns


def _empty_store() -> dict[str, Any]:
    return {"version": 1, "reviews": []}


def _read_store(path: Path) -> dict[str, Any]:
    if not path.exists():
        return _empty_store()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ReviewValidationError("Không thể đọc kho kế hoạch duyệt.") from exc
    if data.get("version") != 1 or not isinstance(data.get("reviews"), list):
        raise ReviewValidationError("Kho kế hoạch duyệt không đúng định dạng.")
    return data


def _write_store(path: Path, store: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(store, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)


def _find(store: dict[str, Any], review_id: str) -> dict[str, Any]:
    review = next((item for item in store["reviews"] if item.get("id") == review_id), None)
    if not review:
        raise ReviewValidationError("Không tìm thấy kế hoạch cần duyệt.")
    return review


def _public_review(review: dict[str, Any], include_payload: bool = True) -> dict[str, Any]:
    result = deepcopy(review)
    if not include_payload:
        result.pop("payload", None)
        result.pop("tree", None)
        result.pop("meta_result", None)
    return result


def submit_review(
    payload: dict[str, Any],
    store_path: Path = DEFAULT_REVIEW_STORE_PATH,
) -> tuple[dict[str, Any], bool]:
    snapshot = _snapshot(payload)
    plan = preview_plan(snapshot)
    digest = _payload_hash(snapshot)
    path = Path(store_path)
    with _STORE_LOCK:
        store = _read_store(path)
        existing = next(
            (
                item
                for item in store["reviews"]
                if item.get("payload_hash") == digest
                and item.get("status") in {"PENDING_REVIEW", "APPROVED", "PUBLISHING", "META_CREATED"}
            ),
            None,
        )
        if existing:
            return _public_review(existing), True
        created_at = _now()
        review = {
            "id": uuid.uuid4().hex,
            "status": "PENDING_REVIEW",
            "payload_hash": digest,
            "submitted_by": str(payload.get("submitted_by") or "Content").strip()[:100] or "Content",
            "submitted_at": created_at,
            "updated_at": created_at,
            "reviewed_at": None,
            "reviewed_by": None,
            "reviewer_note": "",
            "summary": {
                **plan["summary"],
                "campaigns_count": len({flow["campaign_code"] for flow in plan["flows"]}),
                "adsets_count": len(plan["flows"]),
                "ads_count": len(plan["items"]),
            },
            "payload": snapshot,
            "tree": _build_tree(plan),
            "meta_result": None,
        }
        store["reviews"].insert(0, review)
        _write_store(path, store)
        return _public_review(review), False


def list_reviews(store_path: Path = DEFAULT_REVIEW_STORE_PATH) -> list[dict[str, Any]]:
    with _STORE_LOCK:
        store = _read_store(Path(store_path))
        return [_public_review(item, include_payload=False) for item in store["reviews"]]


def get_review(review_id: str, store_path: Path = DEFAULT_REVIEW_STORE_PATH) -> dict[str, Any]:
    with _STORE_LOCK:
        return _public_review(_find(_read_store(Path(store_path)), review_id))


def decide_review(
    review_id: str,
    decision: str,
    reviewer: str,
    note: str = "",
    store_path: Path = DEFAULT_REVIEW_STORE_PATH,
) -> dict[str, Any]:
    if decision not in {"APPROVED", "REJECTED"}:
        raise ReviewValidationError("Quyết định duyệt không hợp lệ.")
    clean_note = str(note or "").strip()[:1000]
    if decision == "REJECTED" and not clean_note:
        raise ReviewValidationError("Cần nhập lý do từ chối.")
    path = Path(store_path)
    with _STORE_LOCK:
        store = _read_store(path)
        review = _find(store, review_id)
        if review["status"] != "PENDING_REVIEW":
            raise ReviewValidationError("Chỉ kế hoạch đang chờ duyệt mới có thể duyệt hoặc từ chối.")
        timestamp = _now()
        review.update(
            {
                "status": decision,
                "reviewed_at": timestamp,
                "reviewed_by": str(reviewer or "IT/Ads Operator").strip()[:100] or "IT/Ads Operator",
                "reviewer_note": clean_note,
                "updated_at": timestamp,
            }
        )
        _write_store(path, store)
        return _public_review(review)


def publish_review(
    review_id: str,
    publish_func: Callable[[dict[str, Any]], dict[str, Any]],
    store_path: Path = DEFAULT_REVIEW_STORE_PATH,
) -> dict[str, Any]:
    path = Path(store_path)
    with _STORE_LOCK:
        store = _read_store(path)
        review = _find(store, review_id)
        if review["status"] == "META_CREATED":
            return _public_review(review)
        if review["status"] != "APPROVED":
            raise ReviewValidationError("Kế hoạch phải được duyệt trước khi tạo trên Meta.")
        review["status"] = "PUBLISHING"
        review["updated_at"] = _now()
        payload = deepcopy(review["payload"])
        _write_store(path, store)
    try:
        result = publish_func(payload)
    except Exception:
        with _STORE_LOCK:
            store = _read_store(path)
            review = _find(store, review_id)
            if review["status"] == "PUBLISHING":
                review["status"] = "APPROVED"
                review["updated_at"] = _now()
                _write_store(path, store)
        raise
    with _STORE_LOCK:
        store = _read_store(path)
        review = _find(store, review_id)
        review.update(
            {
                "status": "META_CREATED",
                "meta_result": deepcopy(result),
                "published_at": _now(),
                "updated_at": _now(),
            }
        )
        _write_store(path, store)
        return _public_review(review)
