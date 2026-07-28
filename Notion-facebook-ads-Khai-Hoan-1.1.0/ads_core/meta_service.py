from __future__ import annotations

import hashlib
import json
import os
import threading
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlencode, urlparse
from urllib.request import Request, urlopen

from ads_core.planner_service import preview_plan


DEFAULT_META_LEDGER_PATH = Path(__file__).resolve().parent.parent / ".web_state" / "meta_publish_ledger.json"
_META_LEDGER_LOCK = threading.Lock()

OBJECTIVES = {
    "AWARENESS_BASE": "OUTCOME_AWARENESS",
    "ENG_BASE": "OUTCOME_ENGAGEMENT",
    "TRAFFIC_BASE": "OUTCOME_TRAFFIC",
    "LEADS_BASE": "OUTCOME_LEADS",
    "SALES_BASE": "OUTCOME_SALES",
}
ZERO_DECIMAL_CURRENCIES = {
    "BIF",
    "CLP",
    "DJF",
    "GNF",
    "JPY",
    "KMF",
    "KRW",
    "MGA",
    "PYG",
    "RWF",
    "UGX",
    "VND",
    "VUV",
    "XAF",
    "XOF",
    "XPF",
}
ADSET_TEMPLATE_FIELDS = (
    "id,name,account_id,effective_status,billing_event,optimization_goal,"
    "bid_strategy,bid_amount,targeting,promoted_object,destination_type,"
    "attribution_spec,optimization_sub_event,is_dynamic_creative,pacing_type"
)
ADSET_CREATE_FIELDS = (
    "billing_event",
    "optimization_goal",
    "bid_strategy",
    "bid_amount",
    "targeting",
    "promoted_object",
    "destination_type",
    "is_dynamic_creative",
    "pacing_type",
)


class MetaValidationError(ValueError):
    pass


class MetaApiError(RuntimeError):
    def __init__(self, message: str, *, code: int | None = None, subcode: int | None = None):
        super().__init__(message)
        self.code = code
        self.subcode = subcode


@dataclass(frozen=True)
class MetaConfig:
    access_token: str
    api_version: str
    ad_account_id: str
    page_id: str
    adset_template_map: dict[str, str]
    default_adset_template_id: str
    allow_default_template: bool
    test_mode: bool

    @classmethod
    def from_env(cls) -> "MetaConfig":
        token = os.environ.get("META_ACCESS_TOKEN", "").strip()
        account = os.environ.get("META_AD_ACCOUNT_ID", "").strip()
        if account and not account.startswith("act_"):
            account = f"act_{account}"
        raw_map = os.environ.get("META_ADSET_TEMPLATE_MAP", "").strip()
        try:
            template_map = json.loads(raw_map) if raw_map else {}
        except json.JSONDecodeError as exc:
            raise MetaValidationError("META_ADSET_TEMPLATE_MAP phải là JSON hợp lệ.") from exc
        if not isinstance(template_map, dict):
            raise MetaValidationError("META_ADSET_TEMPLATE_MAP phải là một JSON object.")
        return cls(
            access_token=token,
            api_version=os.environ.get("META_API_VERSION", "v25.0").strip() or "v25.0",
            ad_account_id=account,
            page_id=os.environ.get("META_PAGE_ID", "").strip(),
            adset_template_map={str(key): str(value) for key, value in template_map.items() if value},
            default_adset_template_id=os.environ.get("META_TEMPLATE_ADSET_ID", "").strip(),
            allow_default_template=os.environ.get("META_ALLOW_DEFAULT_TEMPLATE", "").lower() in {"1", "true", "yes"},
            test_mode=os.environ.get("META_TEST_MODE", "true").lower() not in {"0", "false", "no"},
        )

    def validate(self, *, require_page: bool = False) -> None:
        missing = []
        if not self.access_token:
            missing.append("META_ACCESS_TOKEN")
        if not self.ad_account_id:
            missing.append("META_AD_ACCOUNT_ID")
        if require_page and not self.page_id:
            missing.append("META_PAGE_ID")
        if missing:
            raise MetaValidationError(f"Thiếu cấu hình Meta backend: {', '.join(missing)}.")

    def template_for(self, adset_code: str) -> str:
        template_id = self.adset_template_map.get(adset_code)
        if template_id:
            return template_id
        if self.allow_default_template and self.default_adset_template_id:
            return self.default_adset_template_id
        raise MetaValidationError(
            f"Chưa ánh xạ ad set mẫu Meta cho {adset_code}. "
            "Hãy thêm ID vào META_ADSET_TEMPLATE_MAP trước khi tạo."
        )


class MetaClient:
    def __init__(self, config: MetaConfig, timeout: int = 30, access_token: str | None = None):
        self.config = config
        self.timeout = timeout
        self._access_token = access_token or config.access_token

    def request(self, method: str, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        safe_path = path.lstrip("/")
        url = f"https://graph.facebook.com/{self.config.api_version}/{safe_path}"
        encoded: dict[str, str] = {}
        for key, value in (params or {}).items():
            if value is None:
                continue
            encoded[key] = json.dumps(value, ensure_ascii=False) if isinstance(value, (dict, list, bool)) else str(value)
        body = None
        if method.upper() == "GET" and encoded:
            url = f"{url}?{urlencode(encoded)}"
        elif encoded:
            body = urlencode(encoded).encode("utf-8")
        request = Request(
            url,
            data=body,
            method=method.upper(),
            headers={
                "Authorization": f"Bearer {self._access_token}",
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept": "application/json",
            },
        )
        try:
            with urlopen(request, timeout=self.timeout) as response:
                result = json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            try:
                response_data = json.loads(exc.read().decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                response_data = {}
            error = response_data.get("error") or {}
            message = error.get("error_user_msg") or error.get("message") or f"Meta API trả về HTTP {exc.code}."
            raise MetaApiError(
                str(message),
                code=error.get("code"),
                subcode=error.get("error_subcode"),
            ) from exc
        except (URLError, TimeoutError) as exc:
            raise MetaApiError("Không thể kết nối Meta API.") from exc
        if not isinstance(result, dict):
            raise MetaApiError("Meta API trả về dữ liệu không hợp lệ.")
        return result

    def get(self, path: str, **params: Any) -> dict[str, Any]:
        return self.request("GET", path, params)

    def post(self, path: str, **params: Any) -> dict[str, Any]:
        return self.request("POST", path, params)

    def delete(self, path: str, **params: Any) -> dict[str, Any]:
        return self.request("DELETE", path, params)

    def with_access_token(self, access_token: str) -> "MetaClient":
        if not access_token:
            raise MetaValidationError("Meta không cấp Page Access Token cho Page đã chọn.")
        return MetaClient(self.config, timeout=self.timeout, access_token=access_token)


def _safe_account(account: dict[str, Any], config: MetaConfig) -> dict[str, Any]:
    return {
        "id": account.get("id") or config.ad_account_id,
        "name": account.get("name", ""),
        "currency": account.get("currency", ""),
        "timezone_name": account.get("timezone_name", ""),
        "account_status": account.get("account_status"),
    }


def get_meta_status(config: MetaConfig, client: MetaClient | None = None, *, verify: bool = False) -> dict[str, Any]:
    configured = bool(config.access_token and config.ad_account_id)
    result: dict[str, Any] = {
        "configured": configured,
        "api_version": config.api_version,
        "test_mode": config.test_mode,
        "account_id": config.ad_account_id,
        "page_configured": bool(config.page_id),
        "template_codes": sorted(config.adset_template_map),
        "default_template_enabled": bool(config.allow_default_template and config.default_adset_template_id),
    }
    if verify:
        config.validate()
        api = client or MetaClient(config)
        account = api.get(
            config.ad_account_id,
            fields="id,name,account_status,currency,timezone_name",
        )
        result["account"] = _safe_account(account, config)
        result["connected"] = True
    return result


def _normalize_permalink(value: str) -> str:
    parsed = urlparse(value.strip())
    host = parsed.netloc.lower().removeprefix("www.").removeprefix("m.")
    path = parsed.path.rstrip("/")
    return f"{host}{path}".lower()


def story_id_from_link(link: str, page_id: str) -> str | None:
    parsed = urlparse(link)
    path_parts = [part for part in parsed.path.split("/") if part]
    query = parse_qs(parsed.query)
    story_fbid = (query.get("story_fbid") or query.get("fbid") or [""])[-1]
    query_page_id = (query.get("id") or [""])[-1]
    if story_fbid.isdigit() and query_page_id.isdigit():
        return f"{query_page_id}_{story_fbid}"
    for part in reversed(path_parts):
        if "_" in part:
            left, _, right = part.partition("_")
            if left.isdigit() and right.isdigit():
                return f"{left}_{right}"
    if page_id:
        for marker in ("posts", "photos"):
            if marker in path_parts:
                index = path_parts.index(marker)
                if index + 1 < len(path_parts) and path_parts[index + 1].isdigit():
                    return f"{page_id}_{path_parts[index + 1]}"
    if "reel" in path_parts:
        index = path_parts.index("reel")
        if index + 1 < len(path_parts) and path_parts[index + 1].isdigit():
            return path_parts[index + 1]
    return None


_direct_story_id = story_id_from_link


def resolve_existing_posts(
    links: list[str],
    config: MetaConfig,
    client: MetaClient,
    *,
    strict: bool = True,
) -> dict[str, str]:
    resolved: dict[str, str] = {}
    unresolved: list[str] = []
    for link in links:
        direct = _direct_story_id(link, config.page_id)
        if direct:
            resolved[link] = direct
        else:
            unresolved.append(link)
    if not unresolved:
        return resolved

    page_client = get_page_client(config, client)
    target_links = {_normalize_permalink(link): link for link in unresolved}
    path = f"{config.page_id}/published_posts"
    params: dict[str, Any] = {"fields": "id,permalink_url", "limit": 100}
    for _ in range(20):
        page = page_client.get(path, **params)
        for post in page.get("data", []):
            permalink = post.get("permalink_url")
            story_id = post.get("id")
            if permalink and story_id:
                original = target_links.get(_normalize_permalink(permalink))
                if original:
                    resolved[original] = story_id
        if all(link in resolved for link in links):
            break
        next_url = (page.get("paging") or {}).get("next")
        if not next_url:
            break
        parsed = urlparse(next_url)
        path = parsed.path.split(f"/{config.api_version}/", 1)[-1]
        params = {key: values[-1] for key, values in parse_qs(parsed.query).items() if values}
    missing = [link for link in links if link not in resolved]
    if missing and strict:
        raise MetaValidationError(
            "Không tìm thấy bài viết qua Meta API: "
            + ", ".join(missing[:3])
            + (f" (và {len(missing) - 3} link khác)" if len(missing) > 3 else "")
        )
    return resolved


def get_page_client(config: MetaConfig, client: MetaClient) -> MetaClient:
    config.validate(require_page=True)
    accounts = client.get(
        "me/accounts",
        fields="id,name,tasks,access_token",
        limit=100,
    )
    page_asset = next(
        (item for item in accounts.get("data", []) if str(item.get("id") or "") == config.page_id),
        None,
    )
    if not page_asset:
        raise MetaValidationError(
            f"System User chưa được gán quyền cho Page {config.page_id}."
        )
    page_token = str(page_asset.get("access_token") or "")
    if not page_token:
        raise MetaValidationError(
            f"Meta không cấp Page Access Token cho Page {config.page_id}."
        )
    return client.with_access_token(page_token)


def _minor_amount(value: Any, currency: str) -> int:
    try:
        amount = Decimal(str(value).replace(",", "."))
    except InvalidOperation as exc:
        raise MetaValidationError("Ngân sách phải là một số hợp lệ.") from exc
    multiplier = Decimal(1 if currency.upper() in ZERO_DECIMAL_CURRENCIES else 100)
    minor = int((amount * multiplier).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    if minor <= 0:
        raise MetaValidationError("Ngân sách phải lớn hơn 0.")
    return minor


def _flow_intent(flow: dict[str, Any], currency: str, config: MetaConfig) -> dict[str, Any]:
    objective = OBJECTIVES.get(flow["campaign_code"])
    if not objective:
        raise MetaValidationError(f"Chưa hỗ trợ mục tiêu Meta cho {flow['campaign_code']}.")
    custom = flow.get("custom_budget_values") or {}
    if "Ngân sách trọn đời" in custom:
        budget_field = "lifetime_budget"
        amount = custom["Ngân sách trọn đời"]
    elif "Ngân sách/ngày" in custom:
        budget_field = "daily_budget"
        amount = custom["Ngân sách/ngày"]
    else:
        raise MetaValidationError("Mỗi cách chạy phải có ngân sách tùy chỉnh.")
    return {
        "position": flow["position"],
        "campaign_code": flow["campaign_code"],
        "campaign_name": flow["campaign_name"],
        "objective": objective,
        "adset_code": flow["adset_code"],
        "adset_name": flow["adset_name"],
        "source_adset_id": config.template_for(flow["adset_code"]),
        "budget_field": budget_field,
        "budget_major": str(amount),
        "budget_minor": _minor_amount(amount, currency),
        "currency": currency,
        "start_time": flow.get("start_time"),
        "end_time": flow.get("end_time"),
        "status": "PAUSED",
    }


def preview_meta_plan(
    payload: dict[str, Any],
    config: MetaConfig,
    client: MetaClient | None = None,
) -> dict[str, Any]:
    config.validate()
    plan = preview_plan(payload)
    api = client or MetaClient(config)
    account = api.get(
        config.ad_account_id,
        fields="id,name,account_status,currency,timezone_name",
    )
    if account.get("account_status") not in (None, 1):
        raise MetaValidationError(f"Tài khoản quảng cáo chưa hoạt động (status {account.get('account_status')}).")
    currency = str(account.get("currency") or "").upper()
    if not currency:
        raise MetaValidationError("Không đọc được đơn vị tiền tệ của tài khoản quảng cáo.")
    stories = resolve_existing_posts(plan["links"], config, api)
    flows = []
    for planned_flow in plan["flows"]:
        flow = _flow_intent(planned_flow, currency, config)
        flow["links"] = [
            {"url": link, "object_story_id": stories[link]}
            for link in planned_flow["links"]
        ]
        flows.append(flow)
    templates: dict[str, dict[str, Any]] = {}
    for template_id in {flow["source_adset_id"] for flow in flows}:
        template = api.get(template_id, fields=ADSET_TEMPLATE_FIELDS)
        if not template.get("id"):
            raise MetaValidationError(f"Không đọc được ad set mẫu Meta {template_id}.")
        template_account = template.get("account_id")
        if isinstance(template_account, dict):
            template_account = template_account.get("id")
        if template_account:
            normalized_template_account = str(template_account)
            if not normalized_template_account.startswith("act_"):
                normalized_template_account = f"act_{normalized_template_account}"
            if normalized_template_account != config.ad_account_id:
                raise MetaValidationError(f"Ad set mẫu {template_id} không thuộc tài khoản đang chọn.")
        if template.get("effective_status") in {"ARCHIVED", "DELETED"}:
            raise MetaValidationError(f"Ad set mẫu {template_id} không còn sử dụng được.")
        templates[template_id] = {
            "id": str(template["id"]),
            "name": template.get("name", ""),
            "effective_status": template.get("effective_status"),
            "create_spec": {
                key: template[key]
                for key in ADSET_CREATE_FIELDS
                if key in template and template[key] not in (None, "", [])
            },
        }
    for flow in flows:
        flow["source_adset"] = templates[flow["source_adset_id"]]
    return {
        "valid": True,
        "write_mode": "PAUSED_ONLY",
        "account": _safe_account(account, config),
        "summary": {
            **plan["summary"],
            "campaigns_count": len({flow["campaign_code"] for flow in flows}),
            "adsets_count": len(flows),
            "ads_count": len(plan["items"]),
        },
        "links": [{"url": link, "object_story_id": stories[link]} for link in plan["links"]],
        "flows": flows,
    }


def _ledger_key(payload: dict[str, Any], account_id: str) -> str:
    clean_payload = {
        **payload,
        "flows": [{key: value for key, value in flow.items() if key != "id"} for flow in payload.get("flows", [])],
    }
    source = json.dumps(
        {"account_id": account_id, "payload": clean_payload},
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(source.encode("utf-8")).hexdigest()


def _read_ledger(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"version": 1, "operations": {}}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"version": 1, "operations": {}}
    if data.get("version") != 1 or not isinstance(data.get("operations"), dict):
        return {"version": 1, "operations": {}}
    return data


def _write_ledger(path: Path, ledger: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(ledger, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)


def _today_name(name: str) -> str:
    return f"{name} · {datetime.now().strftime('%Y-%m-%d')}"


def create_paused_meta_drafts(
    payload: dict[str, Any],
    config: MetaConfig,
    client: MetaClient | None = None,
    ledger_path: Path = DEFAULT_META_LEDGER_PATH,
) -> dict[str, Any]:
    api = client or MetaClient(config)
    operation_key = _ledger_key(payload, config.ad_account_id)
    ad_name = str(payload.get("ad_name") or "").strip()
    with _META_LEDGER_LOCK:
        ledger = _read_ledger(Path(ledger_path))
        existing_operation = ledger["operations"].get(operation_key)
        if existing_operation and existing_operation.get("status") == "completed":
            existing_flows = existing_operation.get("flows", {})
            existing_ads = sum(len(flow.get("ads", {})) for flow in existing_flows.values())
            return {
                "operation_key": operation_key,
                "status": "skipped",
                "reason": "Kế hoạch này đã được tạo trên Meta trước đó.",
                "created": 0,
                "skipped": existing_ads,
                "failed": 0,
                "objects": existing_flows,
            }
        preview = preview_meta_plan(payload, config, api)
        operation = ledger["operations"].setdefault(
            operation_key,
            {
                "created_at": datetime.now().isoformat(timespec="seconds"),
                "account_id": config.ad_account_id,
                "status": "in_progress",
                "campaigns": {},
                "flows": {},
            },
        )
        creative_by_story = {
            story_id: str(ad_state["creative_id"])
            for saved_flow in operation.get("flows", {}).values()
            for story_id, ad_state in saved_flow.get("ads", {}).items()
            if ad_state.get("creative_id")
        }
        try:
            for flow in preview["flows"]:
                flow_key = str(flow["position"])
                state = operation["flows"].setdefault(flow_key, {"ads": {}})
                campaigns = operation.setdefault("campaigns", {})
                campaign_state = campaigns.setdefault(flow["campaign_code"], {})
                if not campaign_state.get("campaign_id"):
                    campaign = api.post(
                        f"{config.ad_account_id}/campaigns",
                        name=_today_name(flow["campaign_name"]),
                        objective=flow["objective"],
                        status="PAUSED",
                        special_ad_categories=[],
                        is_adset_budget_sharing_enabled=False,
                    )
                    campaign_state["campaign_id"] = str(campaign["id"])
                    _write_ledger(Path(ledger_path), ledger)
                state["campaign_id"] = campaign_state["campaign_id"]
                if not state.get("adset_id"):
                    adset_params = {
                        "campaign_id": state["campaign_id"],
                        "name": _today_name(flow["adset_name"]),
                        "status": "PAUSED",
                        flow["budget_field"]: flow["budget_minor"],
                        "start_time": flow["start_time"],
                    }
                    if flow.get("end_time"):
                        adset_params["end_time"] = flow["end_time"]
                    adset_params.update(flow["source_adset"]["create_spec"])
                    created_adset = api.post(f"{config.ad_account_id}/adsets", **adset_params)
                    state["adset_id"] = str(created_adset["id"])
                    state["adset_configured"] = True
                    _write_ledger(Path(ledger_path), ledger)
                elif not state.get("adset_configured"):
                    # Compatibility for a partially completed operation created by the
                    # former copy-based implementation. Meta does not allow changing
                    # start_time after a copied ad set has already started.
                    update = {
                        "name": _today_name(flow["adset_name"]),
                        "status": "PAUSED",
                        flow["budget_field"]: flow["budget_minor"],
                    }
                    if flow.get("end_time"):
                        update["end_time"] = flow["end_time"]
                    api.post(state["adset_id"], **update)
                    state["adset_configured"] = True
                    state["schedule_warning"] = "Meta giữ start_time do ad set này được tạo dở bằng cơ chế copy cũ."
                    _write_ledger(Path(ledger_path), ledger)
                for link_index, link in enumerate(flow["links"], start=1):
                    story_id = link["object_story_id"]
                    ad_state = state["ads"].setdefault(story_id, {"link": link["url"]})
                    if ad_state.get("ad_id"):
                        continue
                    if not ad_state.get("creative_id"):
                        creative_id = creative_by_story.get(story_id)
                        if not creative_id:
                            creative = api.post(
                                f"{config.ad_account_id}/adcreatives",
                                name=f"Planner existing post · {story_id}",
                                object_story_id=story_id,
                            )
                            creative_id = str(creative["id"])
                            creative_by_story[story_id] = creative_id
                        ad_state["creative_id"] = creative_id
                        _write_ledger(Path(ledger_path), ledger)
                    if len(preview["links"]) == 1 and ad_name:
                        chosen_name = (
                            ad_name
                            if len(preview["flows"]) == 1
                            else f"{ad_name} · {flow['adset_name']}"
                        )
                    else:
                        chosen_name = f"Bài quảng cáo {link_index} · {flow['adset_name']}"
                    ad = api.post(
                        f"{config.ad_account_id}/ads",
                        name=chosen_name,
                        adset_id=state["adset_id"],
                        creative={"creative_id": ad_state["creative_id"]},
                        status="PAUSED",
                    )
                    ad_state["ad_id"] = str(ad["id"])
                    _write_ledger(Path(ledger_path), ledger)
            operation["status"] = "completed"
            operation["completed_at"] = datetime.now().isoformat(timespec="seconds")
            _write_ledger(Path(ledger_path), ledger)
        except Exception:
            operation["status"] = "partial"
            operation["updated_at"] = datetime.now().isoformat(timespec="seconds")
            _write_ledger(Path(ledger_path), ledger)
            raise

    created_ads = sum(len(flow.get("ads", {})) for flow in operation["flows"].values())
    return {
        "operation_key": operation_key,
        "status": "created",
        "created": created_ads,
        "skipped": 0,
        "failed": 0,
        "write_mode": "PAUSED_ONLY",
        "account": preview["account"],
        "objects": operation["flows"],
    }
