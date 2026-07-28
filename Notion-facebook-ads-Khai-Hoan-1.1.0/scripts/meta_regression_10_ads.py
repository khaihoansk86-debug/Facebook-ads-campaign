from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import bulk_ads_tool as tool
from ads_core.meta_service import MetaClient, MetaConfig, create_paused_meta_drafts
from ads_core.review_service import decide_review, publish_review, submit_review


TARGET_ACCOUNT = "act_1328593895341351"
TEST_NAME_PATTERN = re.compile(r"(api\s*test|kh api regression|regression)", re.IGNORECASE)
KNOWN_TEST_CAMPAIGNS = {"120247844587520657", "120247845876500657"}


def load_config() -> MetaConfig:
    # A long-running parent process may still carry the expired Explorer token.
    # Remove only the child-process copy before loading the current backend secret.
    os.environ.pop("META_ACCESS_TOKEN", None)
    tool.load_env(ROOT / ".env")
    config = MetaConfig.from_env()
    config.validate(require_page=True)
    return config


def page_client(api: MetaClient, config: MetaConfig) -> MetaClient:
    accounts = api.get("me/accounts", fields="id,name,tasks,access_token", limit=100)
    asset = next(
        (item for item in accounts.get("data", []) if str(item.get("id") or "") == config.page_id),
        None,
    )
    if not asset:
        raise RuntimeError(f"System User không nhìn thấy Page {config.page_id}.")
    return api.with_access_token(str(asset.get("access_token") or ""))


def recent_links(api: MetaClient, config: MetaConfig, count: int = 5) -> list[str]:
    page_api = page_client(api, config)
    response = page_api.get(
        f"{config.page_id}/published_posts",
        fields="id,permalink_url,created_time",
        limit=100,
    )
    links = []
    for item in response.get("data", []):
        link = str(item.get("permalink_url") or "").strip()
        if link and link not in links:
            links.append(link)
        if len(links) == count:
            break
    if len(links) != count:
        raise RuntimeError(f"Chỉ tìm thấy {len(links)} bài Page, cần {count} bài để hồi quy.")
    return links


def audit(api: MetaClient, config: MetaConfig) -> dict[str, Any]:
    campaigns = api.get(
        f"{config.ad_account_id}/campaigns",
        fields="id,name,status,effective_status,created_time",
        limit=100,
    ).get("data", [])
    status_summary: dict[str, int] = {}
    candidates = []
    for campaign in campaigns:
        status = str(campaign.get("effective_status") or campaign.get("status") or "UNKNOWN")
        status_summary[status] = status_summary.get(status, 0) + 1
        if (
            TEST_NAME_PATTERN.search(str(campaign.get("name") or ""))
            or str(campaign.get("id") or "") in KNOWN_TEST_CAMPAIGNS
        ):
            candidate = {
                key: campaign.get(key)
                for key in ("id", "name", "status", "effective_status", "created_time")
            }
            candidate["adsets_count"] = len(
                api.get(f"{campaign['id']}/adsets", fields="id", limit=100).get("data", [])
            )
            candidate["ads_count"] = len(
                api.get(f"{campaign['id']}/ads", fields="id", limit=100).get("data", [])
            )
            candidates.append(candidate)
    return {
        "account_id": config.ad_account_id,
        "campaign_total": len(campaigns),
        "status_summary": status_summary,
        "cleanup_candidates": candidates,
    }


def build_payload(links: list[str]) -> dict[str, Any]:
    start_time = (datetime.now(timezone(timedelta(hours=7))) + timedelta(hours=2)).replace(
        second=0,
        microsecond=0,
    )
    common = {
        "campaign_code": "ENG_BASE",
        "audience_codes": ["AUD_BROAD_PHAN_THIET"],
        "dataset_code": "DATASET_NONE",
        "budget_code": "BUD_DAILY_800_PHP",
        "custom_budget_values": {"Ngân sách/ngày": "5"},
        "start_time": start_time.isoformat(timespec="minutes"),
        "end_time": None,
        "placement_code": "PLC_FB_MSG_MOBILE",
        "creative_mode": "existing_post",
    }
    return {
        "links": links,
        "flows": [
            {**common, "adset_code": "ENG_POST_COLD"},
            # Use the same proven existing-post template twice. The two planner
            # flows still become two ad sets under one campaign, while avoiding
            # a messaging optimization that rejects ordinary Page posts.
            {**common, "adset_code": "ENG_POST_COLD"},
        ],
        "ad_name": "",
        "submitted_by": "Codex Meta regression",
    }


def object_ids(objects: dict[str, Any]) -> dict[str, list[str]]:
    campaigns = sorted({str(item["campaign_id"]) for item in objects.values() if item.get("campaign_id")})
    adsets = sorted({str(item["adset_id"]) for item in objects.values() if item.get("adset_id")})
    ads = sorted(
        {
            str(ad["ad_id"])
            for item in objects.values()
            for ad in item.get("ads", {}).values()
            if ad.get("ad_id")
        }
    )
    creatives = sorted(
        {
            str(ad["creative_id"])
            for item in objects.values()
            for ad in item.get("ads", {}).values()
            if ad.get("creative_id")
        }
    )
    return {"campaigns": campaigns, "adsets": adsets, "ads": ads, "creatives": creatives}


def merge_ids(*groups: dict[str, list[str]]) -> dict[str, list[str]]:
    return {
        kind: sorted({object_id for group in groups for object_id in group.get(kind, [])})
        for kind in ("campaigns", "adsets", "ads", "creatives")
    }


def ledger_object_ids(path: Path, operation_key: str = "") -> dict[str, list[str]]:
    ledger = json.loads(path.read_text(encoding="utf-8"))
    operations = ledger.get("operations", {})
    if operation_key:
        operations = {operation_key: operations.get(operation_key, {})}
    return merge_ids(
        *[
            object_ids(operation.get("flows", {}))
            for operation in operations.values()
            if isinstance(operation, dict)
        ]
    )


def rename_test_objects(api: MetaClient, ids: dict[str, list[str]], objects: dict[str, Any], stamp: str) -> None:
    for campaign_id in ids["campaigns"]:
        api.post(campaign_id, name=f"KH API REGRESSION 10 ADS · {stamp}")
    for position, item in objects.items():
        api.post(item["adset_id"], name=f"KH TEST GROUP {position} · {stamp}")


def verify_created(
    api: MetaClient,
    ids: dict[str, list[str]],
    objects: dict[str, Any],
) -> dict[str, Any]:
    campaign_rows = []
    adset_rows = []
    ad_rows = []
    for campaign_id in ids["campaigns"]:
        row = api.get(
            campaign_id,
            fields=(
                "id,name,status,effective_status,objective,"
                "adsets.limit(100){id,name,status,effective_status,campaign_id},"
                "ads.limit(100){id,name,status,effective_status,adset_id}"
            ),
        )
        campaign_rows.append(row)
        adset_rows.extend((row.get("adsets") or {}).get("data", []))
        ad_rows.extend((row.get("ads") or {}).get("data", []))
    ads_per_flow = {
        position: len(item.get("ads", {}))
        for position, item in objects.items()
    }
    checks = {
        "one_campaign": len(ids["campaigns"]) == 1,
        "two_adsets": len(ids["adsets"]) == 2,
        "ten_ads": len(ids["ads"]) == 10,
        "five_ads_per_adset": sorted(ads_per_flow.values()) == [5, 5],
        "exact_adset_ids": {str(row.get("id")) for row in adset_rows} == set(ids["adsets"]),
        "exact_ad_ids": {str(row.get("id")) for row in ad_rows} == set(ids["ads"]),
        "shared_campaign": len({row.get("campaign_id") for row in adset_rows}) == 1,
        "all_configured_paused": all(
            row.get("status") == "PAUSED"
            for row in [*campaign_rows, *adset_rows, *ad_rows]
        ),
    }
    return {
        "passed": all(checks.values()),
        "checks": checks,
        "counts": {
            "campaigns": len(campaign_rows),
            "adsets": len(adset_rows),
            "ads": len(ad_rows),
            "ads_per_flow": ads_per_flow,
        },
        "effective_ad_statuses": sorted(
            {str(row.get("effective_status") or "") for row in ad_rows}
        ),
    }


def cleanup_exact(api: MetaClient, ids: dict[str, list[str]]) -> dict[str, Any]:
    results: dict[str, list[dict[str, Any]]] = {
        "ads": [],
        "adsets": [],
        "campaigns": [],
        "creatives": [],
    }
    for kind in ("ads", "adsets", "campaigns", "creatives"):
        for object_id in ids[kind]:
            for attempt in range(3):
                try:
                    response = api.delete(object_id)
                    results[kind].append({"id": object_id, "success": bool(response.get("success", True))})
                    break
                except Exception as exc:
                    message = str(exc)
                    transient = any(
                        marker in message.lower()
                        for marker in ("unexpected error", "try again", "too many calls", "temporar")
                    )
                    if transient and attempt < 2:
                        time.sleep(2 * (attempt + 1))
                        continue
                    results[kind].append({"id": object_id, "success": False, "error": message})
                    break
    return {
        "success": all(item["success"] for items in results.values() for item in items),
        "deleted": {kind: sum(1 for item in items if item["success"]) for kind, items in results.items()},
        "failures": [
            {"kind": kind, **item}
            for kind, items in results.items()
            for item in items
            if not item["success"]
        ],
    }


def known_test_object_ids(api: MetaClient, config: MetaConfig) -> tuple[list[dict[str, Any]], dict[str, list[str]]]:
    campaigns = api.get(
        f"{config.ad_account_id}/campaigns",
        fields="id,name,status,effective_status",
        limit=100,
    ).get("data", [])
    candidates = [
        campaign
        for campaign in campaigns
        if (
            str(campaign.get("id") or "") in KNOWN_TEST_CAMPAIGNS
            or TEST_NAME_PATTERN.search(str(campaign.get("name") or ""))
        )
        and str(campaign.get("status") or "") == "PAUSED"
    ]
    groups = []
    for campaign in candidates:
        campaign_id = str(campaign["id"])
        adsets = api.get(f"{campaign_id}/adsets", fields="id", limit=100).get("data", [])
        ads = api.get(f"{campaign_id}/ads", fields="id", limit=100).get("data", [])
        groups.append(
            {
                "campaigns": [campaign_id],
                "adsets": [str(item["id"]) for item in adsets if item.get("id")],
                "ads": [str(item["id"]) for item in ads if item.get("id")],
                # Existing-post creatives may be shared with legitimate ads in
                # other campaigns. Only the regression ledger can prove a
                # creative was created by this script, so known-campaign cleanup
                # deliberately leaves creatives alone.
                "creatives": [],
            }
        )
    safe_candidates = [
        {
            key: campaign.get(key)
            for key in ("id", "name", "status", "effective_status")
        }
        for campaign in candidates
    ]
    return safe_candidates, merge_ids(*groups)


def run_regression(api: MetaClient, config: MetaConfig) -> dict[str, Any]:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    ledger_path = ROOT / ".web_state" / f"meta_regression_10_{stamp}.json"
    review_path = ROOT / ".web_state" / f"meta_regression_review_{stamp}.json"
    payload = build_payload(recent_links(api, config))
    review, duplicate = submit_review(payload, review_path)
    if duplicate:
        raise RuntimeError("Kế hoạch hồi quy bị nhận diện trùng trước khi tạo.")
    review = decide_review(review["id"], "APPROVED", "Codex regression", "Automated PAUSED regression", review_path)
    created: dict[str, Any] | None = None
    ids = {"campaigns": [], "adsets": [], "ads": [], "creatives": []}
    verification: dict[str, Any] = {}
    idempotency: dict[str, Any] = {}
    cleanup: dict[str, Any] = {}
    try:
        published = publish_review(
            review["id"],
            lambda approved_payload: create_paused_meta_drafts(
                approved_payload,
                config,
                api,
                ledger_path,
            ),
            review_path,
        )
        created = published.get("meta_result") or {}
        ids = object_ids(created.get("objects") or {})
        rename_test_objects(api, ids, created.get("objects") or {}, stamp)
        verification = verify_created(api, ids, created.get("objects") or {})
        repeated = create_paused_meta_drafts(review["payload"], config, api, ledger_path)
        idempotency = {
            "passed": repeated.get("created") == 0 and repeated.get("skipped") == 10,
            "created": repeated.get("created"),
            "skipped": repeated.get("skipped"),
        }
    finally:
        if ledger_path.exists():
            ids = merge_ids(ids, ledger_object_ids(ledger_path))
        if any(ids.values()):
            cleanup = cleanup_exact(api, ids)
    return {
        "review_status": "APPROVED",
        "meta_created": (created or {}).get("created"),
        "structure": verification,
        "idempotency": idempotency,
        "cleanup": cleanup,
        "test_object_ids": ids,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Safe 10-ad Meta regression and exact cleanup.")
    parser.add_argument("mode", choices=("audit", "run", "recover", "cleanup-known"))
    parser.add_argument("--confirm-account", default="")
    parser.add_argument("--ledger", default="")
    parser.add_argument("--operation-key", default="")
    args = parser.parse_args()
    config = load_config()
    if config.ad_account_id != TARGET_ACCOUNT:
        raise SystemExit(f"Chặn thao tác: cấu hình đang trỏ tới {config.ad_account_id}, không phải {TARGET_ACCOUNT}.")
    api = MetaClient(config)
    if args.mode == "audit":
        result = audit(api, config)
    elif args.mode == "run":
        if args.confirm_account != TARGET_ACCOUNT:
            raise SystemExit(f"Muốn chạy thật phải truyền --confirm-account {TARGET_ACCOUNT}.")
        result = run_regression(api, config)
    elif args.mode == "recover":
        if args.confirm_account != TARGET_ACCOUNT:
            raise SystemExit(f"Muốn dọn ledger phải truyền --confirm-account {TARGET_ACCOUNT}.")
        ledger_path = Path(args.ledger) if args.ledger else max(
            (ROOT / ".web_state").glob("meta_regression_10_*.json"),
            key=lambda item: item.stat().st_mtime,
        )
        ids = ledger_object_ids(ledger_path, args.operation_key)
        result = {
            "ledger": ledger_path.name,
            "operation_key": args.operation_key or "ALL",
            "cleanup": cleanup_exact(api, ids),
            "test_object_ids": ids,
        }
    else:
        if args.confirm_account != TARGET_ACCOUNT:
            raise SystemExit(f"Muốn dọn campaign test phải truyền --confirm-account {TARGET_ACCOUNT}.")
        candidates, ids = known_test_object_ids(api, config)
        result = {
            "candidates": candidates,
            "cleanup": cleanup_exact(api, ids),
            "test_object_ids": ids,
        }
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
