from __future__ import annotations

import hashlib
import json
import threading
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

from ads_core.planner_service import preview_plan


DEFAULT_LEDGER_PATH = Path(__file__).resolve().parent.parent / ".web_state" / "draft_ledger.json"
_LEDGER_LOCK = threading.Lock()


def _read_ledger(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"version": 1, "completed": {}}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"version": 1, "completed": {}}
    if data.get("version") != 1 or not isinstance(data.get("completed"), dict):
        return {"version": 1, "completed": {}}
    return data


def _write_ledger(path: Path, ledger: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(ledger, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)


def _task_key(link: str, flow: dict[str, Any], audience_code: str | None, ad_name: str) -> str:
    relevant_flow = {key: value for key, value in flow.items() if key != "id"}
    source = json.dumps(
        {"link": link, "flow": relevant_flow, "audience_code": audience_code, "ad_name": ad_name},
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(source.encode("utf-8")).hexdigest()


def create_drafts_safely(
    payload: dict[str, Any],
    data_source_id: str,
    create_func: Callable[..., list[dict[str, Any]]],
    ledger_path: Path = DEFAULT_LEDGER_PATH,
) -> dict[str, Any]:
    plan = preview_plan(payload)
    flows = payload.get("flows", [])
    ad_name = str(payload.get("ad_name") or "").strip()
    tasks: list[dict[str, Any]] = []
    for link in plan["links"]:
        for flow_index, flow in enumerate(flows):
            normalized_flow = plan["flows"][flow_index]
            audience_codes = flow.get("audience_codes") or [None]
            for audience_code in audience_codes:
                task_name = ad_name if len(plan["links"]) == 1 else ""
                tasks.append(
                    {
                        "key": _task_key(link, flow, audience_code, task_name),
                        "link": link,
                        "flow": flow,
                        "normalized_flow": normalized_flow,
                        "audience_code": audience_code,
                        "ad_name": task_name,
                    }
                )

    results: list[dict[str, Any]] = []
    with _LEDGER_LOCK:
        ledger = _read_ledger(Path(ledger_path))
        completed = ledger["completed"]
        for position, task in enumerate(tasks, start=1):
            if task["key"] in completed:
                completed_item = completed[task["key"]]
                results.append(
                    {
                        "position": position,
                        "status": "skipped",
                        "link": task["link"],
                        "reason": "Mục này đã được tạo trước đó.",
                        "page_ids": completed_item.get("page_ids", []),
                        "page_urls": completed_item.get("page_urls", []),
                    }
                )
                continue
            flow = task["flow"]
            normalized_flow = task["normalized_flow"]
            try:
                created_pages = create_func(
                    data_source_id,
                    task["link"],
                    flow.get("campaign_code"),
                    [flow.get("adset_code")],
                    audience_preset_codes=[task["audience_code"]] if task["audience_code"] else [],
                    dataset_preset_code=flow.get("dataset_code"),
                    budget_preset_code=flow.get("budget_code"),
                    custom_budget_values=normalized_flow.get("custom_budget_values", {}),
                    schedule_values=normalized_flow.get("schedule_values", {}),
                    placement_preset_code=flow.get("placement_code"),
                    creative_mode=flow.get("creative_mode", "existing_post"),
                    ad_name=task["ad_name"] or None,
                )
                page_ids = [page.get("id") for page in created_pages if isinstance(page, dict) and page.get("id")]
                page_urls = [page.get("url") for page in created_pages if isinstance(page, dict) and page.get("url")]
                completed[task["key"]] = {
                    "created_at": datetime.now().isoformat(timespec="seconds"),
                    "page_ids": page_ids,
                    "page_urls": page_urls,
                    "link": task["link"],
                }
                _write_ledger(Path(ledger_path), ledger)
                results.append(
                    {
                        "position": position,
                        "status": "created",
                        "link": task["link"],
                        "page_ids": page_ids,
                        "page_urls": page_urls,
                    }
                )
            except Exception as exc:
                results.append(
                    {
                        "position": position,
                        "status": "failed",
                        "link": task["link"],
                        "error": str(exc),
                    }
                )

    counts = {
        status: sum(1 for result in results if result["status"] == status)
        for status in ("created", "skipped", "failed")
    }
    return {
        "total": len(results),
        "created": counts["created"],
        "skipped": counts["skipped"],
        "failed": counts["failed"],
        "results": results,
    }
