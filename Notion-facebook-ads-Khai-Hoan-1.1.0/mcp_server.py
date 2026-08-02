#!/usr/bin/env python3
"""Private MCP surface for the Khai Hoan Ads Planner.

The server intentionally exposes planning and review-draft operations only.
It never exposes Meta publishing, approval, deletion, or secret-management tools.
It uses newline-delimited JSON-RPC over stdio so OpenAI Secure MCP Tunnel can
run it without opening another LAN or internet port.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

import bulk_ads_tool as tool
from ads_core.creative_preview_service import get_page_posts_by_date
from ads_core.meta_service import MetaApiError, MetaConfig, MetaValidationError, get_meta_audiences
from ads_core.planner_service import PlannerValidationError, preview_plan, public_catalog
from ads_core.preset_service import PresetValidationError, create_preset, list_presets
from ads_core.review_service import (
    DEFAULT_REVIEW_STORE_PATH,
    ReviewValidationError,
    get_review,
    list_reviews,
    submit_review,
)


APP_DIR = Path(__file__).resolve().parent
ENV_PATH = APP_DIR / ".env"
DEFAULT_AUDIT_PATH = APP_DIR / ".web_state" / "mcp_audit.jsonl"
SERVER_NAME = "khai-hoan-ads-planner"
SERVER_VERSION = "0.1.0"
PROTOCOL_VERSION = "2025-06-18"
_AUDIT_LOCK = threading.Lock()

AUDIENCE_NOTION_FIELDS = {
    "Mẫu đối tượng",
    "Loại tệp đối tượng",
    "Vị trí địa lý",
    "Tuổi kiểm soát min",
    "Ngôn ngữ",
    "Loại trừ đối tượng",
    "Đối tượng tuỳ chỉnh",
    "Đối tượng tương tự",
    "Tuổi min",
    "Tuổi max",
    "Giới tính",
    "Nhắm mục tiêu chi tiết",
}
PLACEMENT_NOTION_FIELDS = {
    "Nền tảng quảng cáo",
    "Vị trí Facebook",
    "Vị trí Instagram",
    "Vị trí Messenger",
    "Vị trí Audience Network",
    "Thiết bị",
    "Mở rộng nhắm chọn",
}


class McpToolError(ValueError):
    pass


def _object_schema(properties: dict[str, Any], required: list[str] | None = None) -> dict[str, Any]:
    return {
        "type": "object",
        "properties": properties,
        "required": required or [],
        "additionalProperties": False,
    }


FLOW_SCHEMA = _object_schema(
    {
        "campaign_code": {"type": "string", "minLength": 3, "maxLength": 64},
        "adset_code": {"type": "string", "minLength": 3, "maxLength": 64},
        "audience_codes": {
            "type": "array",
            "items": {"type": "string", "minLength": 3, "maxLength": 64},
            "minItems": 1,
            "maxItems": 20,
        },
        "dataset_code": {"type": "string", "maxLength": 64},
        "budget_code": {"type": "string", "maxLength": 64},
        "budget_type": {"type": "string", "maxLength": 50},
        "custom_budget_values": {"type": "object", "additionalProperties": True},
        "start_time": {"type": ["string", "null"], "maxLength": 40},
        "end_time": {"type": ["string", "null"], "maxLength": 40},
        "placement_code": {"type": "string", "maxLength": 64},
        "creative_mode": {"type": "string", "enum": ["existing_post", "new_creative"]},
        "link_urls": {
            "type": "array",
            "items": {"type": "string", "maxLength": 2048},
            "maxItems": 100,
        },
    },
    ["campaign_code", "adset_code", "audience_codes", "placement_code"],
)


def _planner_payload_schema(*, include_submitter: bool) -> dict[str, Any]:
    properties: dict[str, Any] = {
        "links": {
            "type": "array",
            "items": {"type": "string", "maxLength": 2048},
            "minItems": 1,
            "maxItems": 100,
        },
        "flows": {"type": "array", "items": FLOW_SCHEMA, "minItems": 1, "maxItems": 100},
        "ad_name": {"type": "string", "maxLength": 200},
    }
    required = ["links", "flows"]
    if include_submitter:
        properties["submitted_by"] = {
            "type": "string",
            "minLength": 1,
            "maxLength": 100,
            "description": "Tên nhân viên yêu cầu gửi kế hoạch, dùng cho nhật ký nội bộ.",
        }
        required.append("submitted_by")
    return _object_schema(properties, required)


PRESET_PROPERTIES = {
    "code": {
        "type": "string",
        "pattern": "^[A-Z][A-Z0-9_]{2,63}$",
        "description": "Mã duy nhất viết hoa, ví dụ AUD_WOMEN_25_45_PT.",
    },
    "name": {"type": "string", "minLength": 1, "maxLength": 200},
    "summary": {"type": "string", "maxLength": 1000},
    "notion_values": {
        "type": "object",
        "description": "Các trường nghiệp vụ đúng tên đang dùng trong catalog Planner.",
        "additionalProperties": True,
    },
    "requested_by": {
        "type": "string",
        "minLength": 1,
        "maxLength": 100,
        "description": "Tên nhân viên yêu cầu lưu preset, dùng cho nhật ký nội bộ.",
    },
}


TOOLS: list[dict[str, Any]] = [
    {
        "name": "get_planner_catalog",
        "title": "Đọc catalog Planner",
        "description": (
            "Dùng khi cần hiểu các campaign, nhóm quảng cáo, đối tượng, ngân sách hoặc vị trí "
            "đang được Planner Khải Hoàn hỗ trợ trước khi đề xuất cấu hình."
        ),
        "inputSchema": _object_schema(
            {
                "sections": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": ["campaigns", "adsets", "audiences", "datasets", "budgets", "placements"],
                    },
                    "minItems": 1,
                    "maxItems": 6,
                },
                "campaign_code": {
                    "type": "string",
                    "maxLength": 64,
                    "description": "Nếu có, chỉ trả ad set và audience được campaign này cho phép.",
                },
            }
        ),
        "annotations": {"readOnlyHint": True, "openWorldHint": False},
    },
    {
        "name": "get_page_posts",
        "title": "Lấy bài viết Page theo ngày",
        "description": (
            "Dùng khi cần lấy nội dung, ngày đăng, thumbnail và permalink các bài đã xuất bản "
            "trên Page trong khoảng ngày Việt Nam. Tối đa 90 ngày mỗi lần."
        ),
        "inputSchema": _object_schema(
            {
                "since": {"type": "string", "format": "date", "description": "Ngày bắt đầu YYYY-MM-DD."},
                "until": {"type": "string", "format": "date", "description": "Ngày kết thúc YYYY-MM-DD, có tính ngày này."},
                "limit": {"type": "integer", "minimum": 1, "maximum": 100, "default": 50},
            },
            ["since", "until"],
        ),
        "annotations": {"readOnlyHint": True, "openWorldHint": True},
    },
    {
        "name": "get_meta_audience_assets",
        "title": "Đọc tài sản đối tượng Meta",
        "description": (
            "Dùng trước khi đề xuất Đối tượng tùy chỉnh hoặc Đối tượng tương tự để lấy đúng ID "
            "tài sản hiện có trong tài khoản quảng cáo. Không trả token."
        ),
        "inputSchema": _object_schema(
            {
                "kind": {"type": "string", "enum": ["all", "custom", "lookalike"], "default": "all"},
                "limit": {"type": "integer", "minimum": 1, "maximum": 100, "default": 50},
            }
        ),
        "annotations": {"readOnlyHint": True, "openWorldHint": True},
    },
    {
        "name": "get_saved_presets",
        "title": "Đọc preset đã lưu",
        "description": "Dùng để xem các tệp đối tượng hoặc vị trí quảng cáo đã được lưu trong Planner.",
        "inputSchema": _object_schema(
            {"kind": {"type": "string", "enum": ["audiences", "placements"]}},
            ["kind"],
        ),
        "annotations": {"readOnlyHint": True, "openWorldHint": False},
    },
    {
        "name": "create_audience_preset",
        "title": "Lưu tệp đối tượng",
        "description": (
            "Dùng sau khi người dùng đã xem và đồng ý đề xuất để lưu một tệp đối tượng mới vào Planner. "
            "Hãy gọi get_planner_catalog sections=[audiences] trước để dùng đúng tên trường và tránh trùng mã."
        ),
        "inputSchema": _object_schema(PRESET_PROPERTIES, ["code", "name", "summary", "notion_values", "requested_by"]),
        "annotations": {"readOnlyHint": False, "destructiveHint": False, "idempotentHint": False, "openWorldHint": False},
    },
    {
        "name": "create_placement_preset",
        "title": "Lưu vị trí quảng cáo",
        "description": (
            "Dùng sau khi người dùng đã xem và đồng ý đề xuất để lưu một preset vị trí quảng cáo mới vào Planner. "
            "Hãy gọi get_planner_catalog sections=[placements] trước để dùng đúng tên trường và tránh trùng mã."
        ),
        "inputSchema": _object_schema(PRESET_PROPERTIES, ["code", "name", "summary", "notion_values", "requested_by"]),
        "annotations": {"readOnlyHint": False, "destructiveHint": False, "idempotentHint": False, "openWorldHint": False},
    },
    {
        "name": "preview_planner_plan",
        "title": "Kiểm tra kế hoạch Planner",
        "description": (
            "Dùng để kiểm tra cấu trúc Campaign → Nhóm quảng cáo → Quảng cáo và các lỗi nghiệp vụ. "
            "Chỉ đọc, không lưu và không tạo gì trên Meta."
        ),
        "inputSchema": _planner_payload_schema(include_submitter=False),
        "annotations": {"readOnlyHint": True, "openWorldHint": False},
    },
    {
        "name": "submit_planner_review",
        "title": "Gửi kế hoạch chờ duyệt",
        "description": (
            "Chỉ dùng sau khi người dùng xác nhận cây kế hoạch. Lưu kế hoạch ở trạng thái PENDING_REVIEW "
            "để IT/Ads Operator kiểm tra trong web. Không duyệt và không tạo quảng cáo trên Meta."
        ),
        "inputSchema": _planner_payload_schema(include_submitter=True),
        "annotations": {"readOnlyHint": False, "destructiveHint": False, "idempotentHint": True, "openWorldHint": False},
    },
    {
        "name": "list_planner_reviews",
        "title": "Xem danh sách kế hoạch duyệt",
        "description": "Dùng để theo dõi các kế hoạch đã gửi và trạng thái duyệt; không trả payload chi tiết.",
        "inputSchema": _object_schema(
            {
                "status": {
                    "type": "string",
                    "enum": ["ALL", "PENDING_REVIEW", "APPROVED", "REJECTED", "PUBLISHING", "META_CREATED"],
                    "default": "ALL",
                },
                "limit": {"type": "integer", "minimum": 1, "maximum": 50, "default": 20},
            }
        ),
        "annotations": {"readOnlyHint": True, "openWorldHint": False},
    },
    {
        "name": "get_planner_review",
        "title": "Xem chi tiết kế hoạch duyệt",
        "description": "Dùng khi cần xem cây và cấu hình chi tiết của một kế hoạch theo review_id.",
        "inputSchema": _object_schema(
            {"review_id": {"type": "string", "pattern": "^[a-f0-9]{32}$"}},
            ["review_id"],
        ),
        "annotations": {"readOnlyHint": True, "openWorldHint": False},
    },
]


def _bounded_int(value: Any, *, default: int, minimum: int, maximum: int) -> int:
    if value is None:
        return default
    if isinstance(value, bool):
        raise McpToolError("Giá trị giới hạn phải là số nguyên.")
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise McpToolError("Giá trị giới hạn phải là số nguyên.") from exc
    if parsed < minimum or parsed > maximum:
        raise McpToolError(f"Giá trị giới hạn phải từ {minimum} đến {maximum}.")
    return parsed


def _clean_actor(value: Any) -> str:
    actor = str(value or "").strip()[:100]
    if not actor:
        raise McpToolError("Cần cung cấp tên nhân viên thực hiện.")
    return actor


def _sanitize(value: Any) -> Any:
    sensitive_keys = {
        "access_token",
        "refresh_token",
        "meta_access_token",
        "openai_api_key",
        "planner_approver_key",
        "planner_session_secret",
        "password",
        "secret",
    }
    if isinstance(value, dict):
        return {
            str(key): _sanitize(item)
            for key, item in value.items()
            if str(key).strip().lower() not in sensitive_keys
        }
    if isinstance(value, list):
        return [_sanitize(item) for item in value]
    return value


def _audit_path() -> Path:
    configured = os.environ.get("MCP_AUDIT_LOG")
    return Path(configured).resolve() if configured else DEFAULT_AUDIT_PATH


def _review_store_path() -> Path:
    configured = os.environ.get("PLANNER_REVIEW_STORE")
    return Path(configured).resolve() if configured else DEFAULT_REVIEW_STORE_PATH


def _record_write(tool_name: str, actor: str, target: str, result: dict[str, Any]) -> None:
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "tool": tool_name,
        "actor": actor,
        "target": target[:200],
        "result": {
            key: result.get(key)
            for key in ("id", "code", "name", "status", "deduplicated")
            if key in result
        },
    }
    path = _audit_path()
    with _AUDIT_LOCK:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(entry, ensure_ascii=False, separators=(",", ":")) + "\n")


def _load_meta_config() -> MetaConfig:
    tool.load_env(ENV_PATH)
    return MetaConfig.from_env()


def _get_planner_catalog(arguments: dict[str, Any]) -> dict[str, Any]:
    catalog = public_catalog()
    sections = arguments.get("sections") or ["campaigns", "audiences", "placements", "budgets"]
    if not isinstance(sections, list) or not sections:
        raise McpToolError("sections phải là danh sách không rỗng.")
    allowed = {"campaigns", "adsets", "audiences", "datasets", "budgets", "placements"}
    unknown = [str(item) for item in sections if item not in allowed]
    if unknown:
        raise McpToolError(f"Phần catalog không hợp lệ: {', '.join(unknown)}")
    campaign_code = str(arguments.get("campaign_code") or "").strip()
    result = {section: catalog[section] for section in sections}
    if campaign_code:
        campaign = next((item for item in catalog["campaigns"] if item.get("code") == campaign_code), None)
        if not campaign:
            raise McpToolError("Không tìm thấy campaign_code trong catalog.")
        if "adsets" in result:
            allowed_adsets = set(campaign.get("allowedAdSetBundleCodes") or [])
            result["adsets"] = [item for item in result["adsets"] if item.get("code") in allowed_adsets]
        if "audiences" in result:
            allowed_audiences = set(campaign.get("allowedAudiencePresetCodes") or [])
            result["audiences"] = [item for item in result["audiences"] if item.get("code") in allowed_audiences]
    return {"campaign_code": campaign_code or None, "catalog": result}


def _get_page_posts(arguments: dict[str, Any]) -> dict[str, Any]:
    limit = _bounded_int(arguments.get("limit"), default=50, minimum=1, maximum=100)
    result = get_page_posts_by_date(arguments.get("since"), arguments.get("until"), _load_meta_config())
    posts = result.get("posts") or []
    return {
        **result,
        "posts": posts[:limit],
        "summary": {
            **(result.get("summary") or {}),
            "returned": min(len(posts), limit),
            "limited_for_chat": len(posts) > limit,
        },
    }


def _get_meta_audience_assets(arguments: dict[str, Any]) -> dict[str, Any]:
    kind = str(arguments.get("kind") or "all")
    if kind not in {"all", "custom", "lookalike"}:
        raise McpToolError("kind phải là all, custom hoặc lookalike.")
    limit = _bounded_int(arguments.get("limit"), default=50, minimum=1, maximum=100)
    result = get_meta_audiences(_load_meta_config())
    audiences = result.get("audiences") or []
    if kind != "all":
        audiences = [item for item in audiences if item.get("kind") == kind]
    return {
        "account_id": result.get("account_id"),
        "kind": kind,
        "audiences": audiences[:limit],
        "summary": {"matched": len(audiences), "returned": min(len(audiences), limit)},
    }


def _get_saved_presets(arguments: dict[str, Any]) -> dict[str, Any]:
    kind = str(arguments.get("kind") or "")
    if kind not in {"audiences", "placements"}:
        raise McpToolError("kind phải là audiences hoặc placements.")
    presets = list_presets(kind)
    return {"kind": kind, "presets": presets, "summary": {"total": len(presets)}}


def _clean_notion_values(kind: str, value: Any) -> dict[str, Any]:
    if not isinstance(value, dict) or not value:
        raise McpToolError("notion_values phải là object không rỗng.")
    allowed = AUDIENCE_NOTION_FIELDS if kind == "audiences" else PLACEMENT_NOTION_FIELDS
    unknown = [str(key) for key in value if str(key) not in allowed]
    if unknown:
        raise McpToolError(f"Trường notion_values không được hỗ trợ: {', '.join(unknown)}")
    if len(value) > len(allowed):
        raise McpToolError("notion_values có quá nhiều trường.")
    cleaned: dict[str, Any] = {}
    for raw_key, raw_value in value.items():
        key = str(raw_key)
        if isinstance(raw_value, bool):
            cleaned[key] = raw_value
        elif isinstance(raw_value, (int, float)):
            if isinstance(raw_value, float) and not math.isfinite(raw_value):
                raise McpToolError(f"Giá trị {key} không hợp lệ.")
            cleaned[key] = raw_value
        elif isinstance(raw_value, str):
            text = raw_value.strip()
            if len(text) > 2000:
                raise McpToolError(f"Giá trị {key} dài quá 2000 ký tự.")
            if text:
                cleaned[key] = text
        else:
            raise McpToolError(f"Giá trị {key} phải là chuỗi, số hoặc boolean.")
    if not cleaned:
        raise McpToolError("notion_values không có giá trị sử dụng được.")
    return cleaned


def _create_preset(kind: str, arguments: dict[str, Any], tool_name: str) -> dict[str, Any]:
    actor = _clean_actor(arguments.get("requested_by"))
    name = str(arguments.get("name") or "").strip()
    summary = str(arguments.get("summary") or "").strip()
    if not name or len(name) > 200:
        raise McpToolError("Tên preset phải có từ 1 đến 200 ký tự.")
    if len(summary) > 1000:
        raise McpToolError("Mô tả preset không được dài quá 1000 ký tự.")
    payload = {
        "code": arguments.get("code"),
        "name": name,
        "summary": summary,
        "notionValues": _clean_notion_values(kind, arguments.get("notion_values")),
    }
    preset = create_preset(kind, payload)
    _record_write(tool_name, actor, str(preset.get("code") or ""), preset)
    return {"preset": preset, "saved": True, "requested_by": actor}


def _clean_planner_payload(arguments: dict[str, Any], *, actor_key: str | None = None) -> dict[str, Any]:
    try:
        serialized_size = len(json.dumps(arguments, ensure_ascii=False).encode("utf-8"))
    except (TypeError, ValueError) as exc:
        raise McpToolError("Dữ liệu Planner không phải JSON hợp lệ.") from exc
    if serialized_size > 512 * 1024:
        raise McpToolError("Dữ liệu Planner vượt quá giới hạn 512 KB.")
    links = arguments.get("links")
    flows = arguments.get("flows")
    if not isinstance(links, list) or not 1 <= len(links) <= 100:
        raise McpToolError("Danh sách links phải có từ 1 đến 100 bài.")
    if not isinstance(flows, list) or not 1 <= len(flows) <= 100:
        raise McpToolError("Danh sách flows phải có từ 1 đến 100 cách chạy.")
    if any(not isinstance(link, str) or len(link) > 2048 for link in links):
        raise McpToolError("Mỗi link phải là chuỗi không dài quá 2048 ký tự.")
    if any(not isinstance(flow, dict) for flow in flows):
        raise McpToolError("Mỗi flow phải là một JSON object.")
    ad_name = str(arguments.get("ad_name") or "").strip()
    if len(ad_name) > 200:
        raise McpToolError("Tên quảng cáo không được dài quá 200 ký tự.")
    payload: dict[str, Any] = {"links": links, "flows": flows, "ad_name": ad_name}
    if actor_key:
        payload[actor_key] = _clean_actor(arguments.get(actor_key))
    return payload


def _preview_planner_plan(arguments: dict[str, Any]) -> dict[str, Any]:
    payload = _clean_planner_payload(arguments)
    return {"plan": preview_plan(payload), "write_mode": "READ_ONLY"}


def _submit_planner_review(arguments: dict[str, Any]) -> dict[str, Any]:
    payload = _clean_planner_payload(arguments, actor_key="submitted_by")
    actor = payload["submitted_by"]
    review, deduplicated = submit_review(payload, _review_store_path())
    audit_result = {
        "id": review.get("id"),
        "status": review.get("status"),
        "deduplicated": deduplicated,
    }
    _record_write("submit_planner_review", actor, str(review.get("id") or ""), audit_result)
    return {"review": review, "deduplicated": deduplicated}


def _list_planner_reviews(arguments: dict[str, Any]) -> dict[str, Any]:
    status = str(arguments.get("status") or "ALL")
    allowed = {"ALL", "PENDING_REVIEW", "APPROVED", "REJECTED", "PUBLISHING", "META_CREATED"}
    if status not in allowed:
        raise McpToolError("Trạng thái review không hợp lệ.")
    limit = _bounded_int(arguments.get("limit"), default=20, minimum=1, maximum=50)
    reviews = list_reviews(_review_store_path())
    if status != "ALL":
        reviews = [item for item in reviews if item.get("status") == status]
    return {"status": status, "reviews": reviews[:limit], "summary": {"matched": len(reviews), "returned": min(len(reviews), limit)}}


def _get_planner_review(arguments: dict[str, Any]) -> dict[str, Any]:
    review_id = str(arguments.get("review_id") or "").strip()
    if len(review_id) != 32 or any(character not in "0123456789abcdef" for character in review_id):
        raise McpToolError("review_id không hợp lệ.")
    return {"review": get_review(review_id, _review_store_path())}


TOOL_HANDLERS: dict[str, Callable[[dict[str, Any]], dict[str, Any]]] = {
    "get_planner_catalog": _get_planner_catalog,
    "get_page_posts": _get_page_posts,
    "get_meta_audience_assets": _get_meta_audience_assets,
    "get_saved_presets": _get_saved_presets,
    "create_audience_preset": lambda arguments: _create_preset("audiences", arguments, "create_audience_preset"),
    "create_placement_preset": lambda arguments: _create_preset("placements", arguments, "create_placement_preset"),
    "preview_planner_plan": _preview_planner_plan,
    "submit_planner_review": _submit_planner_review,
    "list_planner_reviews": _list_planner_reviews,
    "get_planner_review": _get_planner_review,
}


def call_tool(name: str, arguments: Any) -> dict[str, Any]:
    handler = TOOL_HANDLERS.get(name)
    if handler is None:
        raise McpToolError(f"Không có MCP tool: {name}")
    if arguments is None:
        arguments = {}
    if not isinstance(arguments, dict):
        raise McpToolError("arguments phải là một JSON object.")
    result = _sanitize(handler(arguments))
    text = json.dumps(result, ensure_ascii=False, separators=(",", ":"))
    return {
        "content": [{"type": "text", "text": text}],
        "structuredContent": result,
        "isError": False,
    }


def _error_tool_result(exc: Exception) -> dict[str, Any]:
    message = str(exc) or "Không thể hoàn tất yêu cầu MCP."
    safe = {"error": {"code": "tool_error", "message": message[:1000]}}
    return {
        "content": [{"type": "text", "text": json.dumps(safe, ensure_ascii=False)}],
        "structuredContent": safe,
        "isError": True,
    }


def handle_request(request: Any) -> dict[str, Any] | None:
    if not isinstance(request, dict):
        return {"jsonrpc": "2.0", "id": None, "error": {"code": -32600, "message": "Invalid Request"}}
    request_id = request.get("id")
    method = request.get("method")
    if method and str(method).startswith("notifications/"):
        return None
    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": {"name": SERVER_NAME, "version": SERVER_VERSION},
                "instructions": (
                    "Đây là Planner quảng cáo Khải Hoàn. Luôn đọc catalog trước khi đề xuất. "
                    "Mọi cấu hình ghi phải được người dùng xác nhận. MCP không có quyền duyệt, publish, "
                    "kích hoạt hoặc xóa quảng cáo; hãy hướng người dùng sang web Planner cho các bước đó."
                ),
            },
        }
    if method == "ping":
        return {"jsonrpc": "2.0", "id": request_id, "result": {}}
    if method == "tools/list":
        return {"jsonrpc": "2.0", "id": request_id, "result": {"tools": TOOLS}}
    if method == "tools/call":
        params = request.get("params") if isinstance(request.get("params"), dict) else {}
        try:
            result = call_tool(str(params.get("name") or ""), params.get("arguments"))
        except (
            McpToolError,
            PlannerValidationError,
            PresetValidationError,
            MetaValidationError,
            MetaApiError,
            ReviewValidationError,
        ) as exc:
            result = _error_tool_result(exc)
        except Exception:
            print("Unexpected MCP tool failure", file=sys.stderr)
            result = _error_tool_result(McpToolError("Lỗi nội bộ khi chạy MCP tool."))
        return {"jsonrpc": "2.0", "id": request_id, "result": result}
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "error": {"code": -32601, "message": "Method not found"},
    }


def serve_stdio(input_stream: Any = None, output_stream: Any = None) -> None:
    source = input_stream or sys.stdin
    destination = output_stream or sys.stdout
    for raw_line in source:
        line = raw_line.strip()
        if not line:
            continue
        try:
            request = json.loads(line)
            response = handle_request(request)
        except json.JSONDecodeError:
            response = {"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "Parse error"}}
        if response is not None:
            destination.write(json.dumps(response, ensure_ascii=False, separators=(",", ":")) + "\n")
            destination.flush()


def main() -> None:
    for stream in (sys.stdin, sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="Khải Hoàn Ads Planner MCP server (stdio).")
    parser.add_argument("--self-test", action="store_true", help="Kiểm tra initialize và tools/list rồi thoát.")
    args = parser.parse_args()
    if args.self_test:
        initialize = handle_request({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}})
        tools_list = handle_request({"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}})
        print(json.dumps({"initialize": initialize, "tools": tools_list}, ensure_ascii=False))
        return
    serve_stdio()


if __name__ == "__main__":
    main()
