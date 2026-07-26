from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Callable

from ads_core.facebook_csv import read_sample_rows, write_facebook_csv


class ExportValidationError(ValueError):
    pass


def candidate_summary(page: dict[str, Any], values: dict[str, Any]) -> dict[str, Any]:
    raw_status = values.get("Trạng thái") or "Chưa có trạng thái"
    display_status = {
        "Ready": "Sẵn sàng",
        "To-do": "Việc cần làm",
        "Not started": "Chưa bắt đầu",
        "In progress": "Đang thực hiện",
        "Done": "Hoàn thành",
    }.get(raw_status, raw_status)
    return {
        "id": page.get("id", ""),
        "url": page.get("url", ""),
        "name": values.get("Tên chiến dịch / bài ads") or values.get("Tên quảng cáo") or "Chưa đặt tên",
        "status": display_status,
        "campaign": values.get("Tên chiến dịch") or values.get("Campaign Name") or "",
        "adset": values.get("Tên nhóm QC") or values.get("Ad Set Name") or "",
        "post_url": values.get("Link bài viết") or values.get("Facebook Post URL") or "",
        "audience": values.get("Mẫu đối tượng") or values.get("Đối tượng tuỳ chỉnh") or "",
        "budget": values.get("Ngân sách/ngày") or values.get("Ngân sách trọn đời") or "",
    }


def list_export_candidates(
    database_id: str,
    query_func: Callable[..., list[dict[str, Any]]],
    values_func: Callable[[dict[str, Any]], dict[str, Any]],
    ready_names: list[str] | None = None,
) -> list[dict[str, Any]]:
    pages = query_func(database_id, include_exported=False, ready_names=ready_names)
    return [candidate_summary(page, values_func(page)) for page in pages]


def export_selected_pages(
    *,
    database_id: str,
    selected_page_ids: list[str],
    sample_csv: str | Path,
    template_row_index: int,
    output_dir: str | Path,
    mapping: dict[str, str],
    query_func: Callable[..., list[dict[str, Any]]],
    build_rows_func: Callable[..., list[dict[str, Any]]],
    mark_exported_func: Callable[..., None],
    ready_names: list[str] | None = None,
    sync_func: Callable[..., bool] | None = None,
) -> dict[str, Any]:
    requested = list(dict.fromkeys(str(page_id) for page_id in selected_page_ids if page_id))
    if not requested:
        raise ExportValidationError("Hãy chọn ít nhất một bài để xuất CSV.")

    eligible_pages = query_func(database_id, include_exported=False, ready_names=ready_names)
    eligible_by_id = {page.get("id"): page for page in eligible_pages if page.get("id")}
    missing = [page_id for page_id in requested if page_id not in eligible_by_id]
    if missing:
        raise ExportValidationError(
            "Một số bài không còn đủ điều kiện xuất. Hãy tải lại danh sách trước khi tiếp tục."
        )
    pages = [eligible_by_id[page_id] for page_id in requested]

    headers, sample_rows = read_sample_rows(sample_csv)
    if not headers:
        raise ExportValidationError("File mẫu Meta không có tiêu đề cột.")
    index = min(max(template_row_index, 0), max(0, len(sample_rows) - 1))
    template_row = dict(sample_rows[index]) if sample_rows else {}
    rows = build_rows_func(pages, headers, template_row, mapping, sample_rows)
    if len(rows) != len(pages):
        raise RuntimeError("Số dòng CSV tạo ra không khớp số bài đã chọn.")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = Path(output_dir) / f"facebook_web_{timestamp}.csv"
    output = write_facebook_csv(output_path, headers, rows)

    for page in pages:
        mark_exported_func(page["id"], page.get("properties", {}))

    sync_warning = ""
    if sync_func:
        try:
            sync_func(database_id, pages, rows, output, sample_csv)
        except Exception as exc:
            sync_warning = str(exc)

    return {
        "count": len(rows),
        "file_name": Path(output).name,
        "output": str(output),
        "page_ids": requested,
        "sync_warning": sync_warning,
    }
