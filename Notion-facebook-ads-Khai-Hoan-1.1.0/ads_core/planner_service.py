from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any
from urllib.parse import urlparse

from ads_core.planner_catalog import load_planner_bundles


class PlannerValidationError(ValueError):
    pass


@dataclass(frozen=True)
class CatalogIndex:
    campaigns: dict[str, dict[str, Any]]
    adsets: dict[str, dict[str, Any]]
    audiences: dict[str, dict[str, Any]]
    datasets: dict[str, dict[str, Any]]
    budgets: dict[str, dict[str, Any]]
    placements: dict[str, dict[str, Any]]


def _index(catalog: dict[str, Any]) -> CatalogIndex:
    def keyed(name: str) -> dict[str, dict[str, Any]]:
        return {item["code"]: item for item in catalog.get(name, []) if item.get("code")}

    return CatalogIndex(
        campaigns=keyed("campaignBundles"),
        adsets=keyed("adSetBundles"),
        audiences=keyed("audiencePresets"),
        datasets=keyed("datasetPresets"),
        budgets=keyed("budgetPresets"),
        placements=keyed("placementPresets"),
    )


def _required(index: dict[str, dict[str, Any]], code: str | None, label: str) -> dict[str, Any]:
    item = index.get(str(code or ""))
    if not item:
        raise PlannerValidationError(f"Không tìm thấy {label}: {code or 'chưa chọn'}")
    return item


def _optional(index: dict[str, dict[str, Any]], code: str | None, label: str) -> dict[str, Any] | None:
    if not code:
        return None
    return _required(index, code, label)


def _clean_links(raw_links: Any) -> list[str]:
    if isinstance(raw_links, str):
        candidates = raw_links.splitlines()
    elif isinstance(raw_links, list):
        candidates = raw_links
    else:
        candidates = []
    links: list[str] = []
    for raw in candidates:
        link = str(raw or "").strip()
        if not link:
            continue
        parsed = urlparse(link)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise PlannerValidationError(f"Đường dẫn không hợp lệ: {link}")
        hostname = (parsed.hostname or "").lower()
        if not (
            hostname == "facebook.com"
            or hostname.endswith(".facebook.com")
            or hostname == "fb.watch"
            or hostname.endswith(".fb.watch")
        ):
            raise PlannerValidationError(f"Không phải đường dẫn Facebook: {link}")
        if link not in links:
            links.append(link)
    return links


def _flow_details(flow: dict[str, Any], catalog_index: CatalogIndex) -> dict[str, Any]:
    campaign = _required(catalog_index.campaigns, flow.get("campaign_code"), "chiến dịch")
    adset = _required(catalog_index.adsets, flow.get("adset_code"), "nhóm quảng cáo")
    if adset.get("campaignBundleCode") != campaign.get("code"):
        raise PlannerValidationError("Nhóm quảng cáo không thuộc chiến dịch đã chọn.")

    allowed_adsets = set(campaign.get("allowedAdSetBundleCodes", []))
    if allowed_adsets and adset.get("code") not in allowed_adsets:
        raise PlannerValidationError("Nhóm quảng cáo không được phép dùng với chiến dịch này.")

    audience_codes = [str(code) for code in flow.get("audience_codes", []) if code]
    if len(audience_codes) != 1:
        raise PlannerValidationError("Mỗi cách chạy phải chọn đúng một nhóm người xem.")
    audiences = [_required(catalog_index.audiences, code, "nhóm người xem") for code in audience_codes]
    allowed_audiences = set(campaign.get("allowedAudiencePresetCodes", []))
    if allowed_audiences and any(item.get("code") not in allowed_audiences for item in audiences):
        raise PlannerValidationError("Nhóm người xem không được phép dùng với chiến dịch này.")

    dataset = _optional(catalog_index.datasets, flow.get("dataset_code"), "nguồn dữ liệu")
    budget = _optional(catalog_index.budgets, flow.get("budget_code"), "ngân sách")
    placement = _optional(catalog_index.placements, flow.get("placement_code"), "vị trí hiển thị")
    if adset.get("requiresDataset") and (not dataset or dataset.get("code") == "DATASET_NONE"):
        raise PlannerValidationError("Nhóm quảng cáo này yêu cầu chọn nguồn dữ liệu.")

    allowed_budget_keys = {"Ngân sách/ngày", "Ngân sách trọn đời"}
    custom_budget: dict[str, Any] = {}
    for key, value in (flow.get("custom_budget_values") or {}).items():
        if value in (None, ""):
            continue
        key = str(key)
        if key not in allowed_budget_keys:
            raise PlannerValidationError(f"Loại ngân sách tùy chỉnh không hợp lệ: {key}")
        normalized = str(value).strip().replace(",", ".")
        try:
            amount = Decimal(normalized)
        except InvalidOperation as exc:
            raise PlannerValidationError("Số tiền tùy chỉnh phải là một số lớn hơn 0.") from exc
        if not amount.is_finite() or amount <= 0:
            raise PlannerValidationError("Số tiền tùy chỉnh phải là một số lớn hơn 0.")
        custom_budget[key] = value if isinstance(value, (int, float)) and not isinstance(value, bool) else normalized
    values: dict[str, Any] = {}
    for item in (campaign, adset, audiences[0] if audiences else None, dataset, budget):
        if item:
            values.update(item.get("notionValues", {}))
    values.update(custom_budget)
    if placement:
        values.update(placement.get("notionValues", {}))

    return {
        "campaign": campaign,
        "adset": adset,
        "audiences": audiences,
        "dataset": dataset,
        "budget": budget,
        "placement": placement,
        "custom_budget_values": custom_budget,
        "creative_mode": flow.get("creative_mode") or "existing_post",
        "notion_values": values,
    }


def public_catalog(catalog: dict[str, Any] | None = None) -> dict[str, Any]:
    source = catalog or load_planner_bundles()
    return {
        "campaigns": source.get("campaignBundles", []),
        "adsets": source.get("adSetBundles", []),
        "audiences": source.get("audiencePresets", []),
        "datasets": source.get("datasetPresets", []),
        "budgets": source.get("budgetPresets", []),
        "placements": source.get("placementPresets", []),
    }


def preview_plan(payload: dict[str, Any], catalog: dict[str, Any] | None = None) -> dict[str, Any]:
    source = catalog or load_planner_bundles()
    catalog_index = _index(source)
    links = _clean_links(payload.get("links", []))
    flows = payload.get("flows") or []
    if not links:
        raise PlannerValidationError("Cần ít nhất một đường dẫn bài viết Facebook.")
    if not isinstance(flows, list) or not flows:
        raise PlannerValidationError("Cần thêm ít nhất một cách chạy.")

    expanded_flows: list[dict[str, Any]] = []
    for position, flow in enumerate(flows, start=1):
        if not isinstance(flow, dict):
            raise PlannerValidationError(f"Cách chạy {position} không hợp lệ.")
        details = _flow_details(flow, catalog_index)
        units = details["audiences"] or [None]
        expanded_flows.append(
            {
                "position": position,
                "campaign_code": details["campaign"]["code"],
                "campaign_name": details["campaign"].get("objectiveName") or details["campaign"].get("name"),
                "adset_code": details["adset"]["code"],
                "adset_name": details["adset"].get("name"),
                "conversion_location": details["adset"].get("conversionLocation"),
                "performance_goal": details["adset"].get("performanceGoal"),
                "audiences": [item.get("name") for item in details["audiences"]],
                "dataset": details["dataset"].get("name") if details["dataset"] else "Không chọn",
                "budget": details["budget"].get("name") if details["budget"] else "Chưa chọn",
                "placement": details["placement"].get("name") if details["placement"] else "Chưa chọn",
                "creative_mode": details["creative_mode"],
                "units": len(units),
                "notion_values": details["notion_values"],
            }
        )

    items = [
        {"link": link, "flow": flow}
        for link in links
        for flow in expanded_flows
        for _ in range(flow["units"])
    ]
    return {
        "valid": True,
        "links": links,
        "flows": expanded_flows,
        "items": items,
        "summary": {
            "links_count": len(links),
            "flows_count": len(expanded_flows),
            "items_count": len(items),
        },
    }
