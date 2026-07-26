from __future__ import annotations

import re
import threading
from copy import deepcopy
from pathlib import Path

from .planner_catalog import PLANNER_BUNDLES_PATH, load_planner_bundles, save_planner_bundles


class PresetValidationError(ValueError):
    pass


_PRESET_KEYS = {
    "audiences": "audiencePresets",
    "placements": "placementPresets",
    "budgets": "budgetPresets",
}
_CODE_PATTERN = re.compile(r"^[A-Z][A-Z0-9_]{2,63}$")
_WRITE_LOCK = threading.Lock()


def _catalog_key(kind: str) -> str:
    try:
        return _PRESET_KEYS[kind]
    except KeyError as exc:
        raise PresetValidationError("Loại bundle không hợp lệ.") from exc


def _clean_payload(payload: dict, *, expected_code: str | None = None) -> dict:
    if not isinstance(payload, dict):
        raise PresetValidationError("Dữ liệu bundle phải là một đối tượng.")
    code = str(payload.get("code") or "").strip().upper()
    if expected_code is not None and code != expected_code:
        raise PresetValidationError("Mã bundle trong đường dẫn và nội dung không khớp.")
    if not _CODE_PATTERN.fullmatch(code):
        raise PresetValidationError("Mã bundle phải có 3–64 ký tự, chỉ gồm chữ in hoa, số và dấu gạch dưới.")
    name = str(payload.get("name") or "").strip()
    if not name:
        raise PresetValidationError("Tên bundle không được để trống.")
    notion_values = payload.get("notionValues", {})
    if not isinstance(notion_values, dict):
        raise PresetValidationError("Các thiết lập của bundle không hợp lệ.")
    cleaned = {
        "code": code,
        "name": name,
        "summary": str(payload.get("summary") or "").strip(),
        "notionValues": {
            str(key).strip(): value
            for key, value in notion_values.items()
            if str(key).strip() and value not in (None, "")
        },
    }
    return cleaned


def list_presets(kind: str, path: str | Path = PLANNER_BUNDLES_PATH) -> list[dict]:
    key = _catalog_key(kind)
    return deepcopy(load_planner_bundles(path).get(key, []))


def create_preset(kind: str, payload: dict, path: str | Path = PLANNER_BUNDLES_PATH) -> dict:
    key = _catalog_key(kind)
    preset = _clean_payload(payload)
    with _WRITE_LOCK:
        catalog = load_planner_bundles(path)
        items = catalog.setdefault(key, [])
        if any(item.get("code") == preset["code"] for item in items):
            raise PresetValidationError("Mã bundle này đã tồn tại.")
        items.append(preset)
        save_planner_bundles(catalog, path)
    return deepcopy(preset)


def update_preset(
    kind: str,
    code: str,
    payload: dict,
    path: str | Path = PLANNER_BUNDLES_PATH,
) -> dict:
    key = _catalog_key(kind)
    normalized_code = str(code).strip().upper()
    preset = _clean_payload(payload, expected_code=normalized_code)
    with _WRITE_LOCK:
        catalog = load_planner_bundles(path)
        items = catalog.setdefault(key, [])
        for index, existing in enumerate(items):
            if existing.get("code") == normalized_code:
                items[index] = {**existing, **preset}
                save_planner_bundles(catalog, path)
                return deepcopy(items[index])
    raise PresetValidationError("Không tìm thấy bundle cần cập nhật.")
