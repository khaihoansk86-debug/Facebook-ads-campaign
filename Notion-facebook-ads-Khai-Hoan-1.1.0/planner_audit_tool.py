from __future__ import annotations

import argparse
import html
import json
import os
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

import bulk_ads_tool as tool


ROOT = Path(__file__).resolve().parent
CATALOG_PATH = ROOT / "config" / "planner_bundles.json"
REPORT_PATH = ROOT / "scratch" / "planner_audit_report.html"

EXPECTED_CAMPAIGN_COUNTS = {
    "ENG_BASE": 21,
    "TRAFFIC_BASE": 11,
    "AWARENESS_BASE": 5,
    "LEADS_BASE": 15,
    "SALES_BASE": 18,
}

REQUIRED_CAMPAIGN_VALUES = ["Tên chiến dịch", "Mục tiêu chiến dịch"]
REQUIRED_ADSET_VALUES = ["Tên nhóm QC", "Vị trí chuyển đổi", "Mục tiêu tối ưu", "Loại bài quảng cáo"]


def esc(value) -> str:
    return html.escape("" if value is None else str(value), quote=True)


def status_label(status: str) -> str:
    return {
        "ok": "OK",
        "warning": "Cần kiểm tra",
        "error": "Lỗi",
        "info": "Ghi chú",
    }.get(status, status)


def issue(status: str, scope: str, message: str, detail: str = "") -> dict:
    return {"status": status, "scope": scope, "message": message, "detail": detail}


def duplicate_values(values: list[str]) -> list[str]:
    return [value for value, count in Counter(values).items() if count > 1 and value]


def audit_catalog() -> dict:
    catalog = tool.load_planner_bundles(CATALOG_PATH)
    campaigns = catalog.get("campaignBundles", [])
    adsets = catalog.get("adSetBundles", [])
    adset_by_code = {item.get("code"): item for item in adsets}
    campaign_by_code = {item.get("code"): item for item in campaigns}

    issues: list[dict] = []

    for kind, items in (("Campaign", campaigns), ("Ad set", adsets)):
        for code in duplicate_values([item.get("code", "") for item in items]):
            issues.append(issue("error", kind, f"Trùng mã bundle: {code}"))

    objective_aliases = tool.VALUE_ALIASES.get("Mục tiêu chiến dịch", {})
    destination_aliases = tool.VALUE_ALIASES.get("Vị trí chuyển đổi", {})
    goal_aliases = tool.VALUE_ALIASES.get("Mục tiêu tối ưu", {})

    for campaign in campaigns:
        code = campaign.get("code", "")
        values = campaign.get("notionValues", {})
        for key in REQUIRED_CAMPAIGN_VALUES:
            if not values.get(key):
                issues.append(issue("error", code, f"Thiếu trường campaign: {key}"))
        objective = values.get("Mục tiêu chiến dịch")
        if objective and objective not in objective_aliases:
            issues.append(issue("error", code, "Mục tiêu chiến dịch chưa có mapping CSV", objective))

        allowed = campaign.get("allowedAdSetBundleCodes", [])
        missing = [adset_code for adset_code in allowed if adset_code not in adset_by_code]
        if missing:
            issues.append(issue("error", code, "allowedAdSetBundleCodes tham chiếu bundle không tồn tại", ", ".join(missing)))

        actual = len(allowed)
        expected = EXPECTED_CAMPAIGN_COUNTS.get(code)
        if expected is not None and actual != expected:
            issues.append(issue("warning", code, f"Số bundle khác baseline đã chuẩn hóa: hiện {actual}, kỳ vọng {expected}"))

    allowed_all = {code for campaign in campaigns for code in campaign.get("allowedAdSetBundleCodes", [])}
    for adset in adsets:
        code = adset.get("code", "")
        campaign_code = adset.get("campaignBundleCode", "")
        values = adset.get("notionValues", {})

        if campaign_code not in campaign_by_code:
            issues.append(issue("error", code, "campaignBundleCode không tồn tại", campaign_code))
        if code not in allowed_all:
            issues.append(issue("warning", code, "Bundle tồn tại nhưng không nằm trong allowedAdSetBundleCodes của campaign nào"))

        for key in REQUIRED_ADSET_VALUES:
            if not values.get(key):
                issues.append(issue("error", code, f"Thiếu trường ad set: {key}"))

        destination = values.get("Vị trí chuyển đổi")
        goal = values.get("Mục tiêu tối ưu")
        if destination and destination not in destination_aliases:
            issues.append(issue("error", code, "Vị trí chuyển đổi chưa có mapping CSV", destination))
        if goal and goal not in goal_aliases:
            issues.append(issue("error", code, "Mục tiêu tối ưu chưa có mapping CSV", goal))

        if adset.get("requiresDataset") and not catalog.get("datasetPresets"):
            issues.append(issue("error", code, "Bundle yêu cầu tập dữ liệu nhưng catalog chưa có datasetPresets"))

        mapped_destination = destination_aliases.get(destination, "")
        if "," in mapped_destination:
            issues.append(
                issue(
                    "info",
                    code,
                    "Vị trí chuyển đổi nhiều vị trí dùng mapping CSV dạng tổ hợp, nên test import thực tế với Meta",
                    f"{destination} -> {mapped_destination}",
                )
            )

    by_campaign: list[dict] = []
    by_location: dict[str, dict[str, list[dict]]] = defaultdict(lambda: defaultdict(list))
    for campaign in campaigns:
        code = campaign.get("code", "")
        allowed = campaign.get("allowedAdSetBundleCodes", [])
        bundles = [adset_by_code[item] for item in allowed if item in adset_by_code]
        by_campaign.append(
            {
                "code": code,
                "name": campaign.get("name", ""),
                "objective": (campaign.get("notionValues") or {}).get("Mục tiêu chiến dịch", ""),
                "count": len(bundles),
                "expected": EXPECTED_CAMPAIGN_COUNTS.get(code),
            }
        )
        for bundle in bundles:
            by_location[code][bundle.get("conversionLocation", "")].append(
                {
                    "code": bundle.get("code", ""),
                    "goal": bundle.get("performanceGoal", ""),
                    "group": bundle.get("conversionLocationGroup", ""),
                    "requiresDataset": bool(bundle.get("requiresDataset")),
                    "creative": bundle.get("defaultCreativeType", ""),
                }
            )

    summary = {
        "campaigns": len(campaigns),
        "adsets": len(adsets),
        "audiencePresets": len(catalog.get("audiencePresets", [])),
        "datasetPresets": len(catalog.get("datasetPresets", [])),
        "budgetPresets": len(catalog.get("budgetPresets", [])),
        "placementPresets": len(catalog.get("placementPresets", [])),
        "errors": sum(1 for item in issues if item["status"] == "error"),
        "warnings": sum(1 for item in issues if item["status"] == "warning"),
        "notes": sum(1 for item in issues if item["status"] == "info"),
    }

    return {
        "generatedAt": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "summary": summary,
        "issues": issues,
        "campaigns": by_campaign,
        "byLocation": {campaign: dict(locations) for campaign, locations in by_location.items()},
    }


def render_report(data: dict) -> str:
    payload = json.dumps(data, ensure_ascii=False)
    cards = "".join(
        f"""
        <section class="card">
          <span>{esc(label)}</span>
          <strong>{esc(value)}</strong>
        </section>
        """
        for label, value in [
            ("Campaign", data["summary"]["campaigns"]),
            ("Ad set bundle", data["summary"]["adsets"]),
            ("Audience preset", data["summary"]["audiencePresets"]),
            ("Dataset preset", data["summary"]["datasetPresets"]),
            ("Budget preset", data["summary"]["budgetPresets"]),
            ("Placement preset", data["summary"]["placementPresets"]),
            ("Lỗi", data["summary"]["errors"]),
            ("Cảnh báo", data["summary"]["warnings"]),
        ]
    )

    issue_rows = "".join(
        f"""
        <tr data-status="{esc(item["status"])}">
          <td><span class="pill {esc(item["status"])}">{esc(status_label(item["status"]))}</span></td>
          <td>{esc(item["scope"])}</td>
          <td>{esc(item["message"])}</td>
          <td>{esc(item.get("detail", ""))}</td>
        </tr>
        """
        for item in data["issues"]
    )
    if not issue_rows:
        issue_rows = '<tr><td colspan="4" class="muted">Không có lỗi hoặc cảnh báo bắt buộc.</td></tr>'

    campaign_rows = "".join(
        f"""
        <tr>
          <td>{esc(item["code"])}</td>
          <td>{esc(item["name"])}</td>
          <td>{esc(item["objective"])}</td>
          <td>{esc(item["count"])}</td>
          <td>{esc(item["expected"] or "")}</td>
        </tr>
        """
        for item in data["campaigns"]
    )

    matrix_sections = []
    campaign_lookup = {item["code"]: item for item in data["campaigns"]}
    for campaign_code, locations in data["byLocation"].items():
        campaign = campaign_lookup.get(campaign_code, {})
        location_blocks = []
        for location, bundles in locations.items():
            bundle_rows = "".join(
                f"""
                <tr>
                  <td>{esc(bundle["code"])}</td>
                  <td>{esc(bundle["goal"])}</td>
                  <td>{esc(bundle["group"])}</td>
                  <td>{'Có' if bundle["requiresDataset"] else 'Không'}</td>
                  <td>{esc(bundle["creative"])}</td>
                </tr>
                """
                for bundle in bundles
            )
            location_blocks.append(
                f"""
                <details open>
                  <summary>{esc(location)} <small>{len(bundles)} goal</small></summary>
                  <table>
                    <thead><tr><th>Mã bundle</th><th>Mục tiêu hiệu quả</th><th>Nhóm</th><th>Cần dataset</th><th>Creative</th></tr></thead>
                    <tbody>{bundle_rows}</tbody>
                  </table>
                </details>
                """
            )
        matrix_sections.append(
            f"""
            <section class="campaign">
              <h3>{esc(campaign_code)} · {esc(campaign.get("objective", ""))}</h3>
              <p>{esc(campaign.get("name", ""))}</p>
              {''.join(location_blocks)}
            </section>
            """
        )

    return f"""<!doctype html>
<html lang="vi">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Planner Audit Tool - Facebook Ads Khai Hoan</title>
  <style>
    :root {{
      --bg: #10151f;
      --panel: #172233;
      --panel-2: #1f3047;
      --line: #324762;
      --text: #f5f7fb;
      --muted: #a7b4c7;
      --ok: #26c281;
      --warn: #f2b84b;
      --err: #ff6b6b;
      --info: #6db7ff;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      background: radial-gradient(circle at top left, #254566 0, transparent 32rem), linear-gradient(135deg, #0d121b, #172234 55%, #10151f);
      color: var(--text);
      font-family: "Segoe UI", sans-serif;
      line-height: 1.45;
    }}
    header {{
      padding: 28px 32px 18px;
      border-bottom: 1px solid rgba(255,255,255,.08);
    }}
    h1 {{ margin: 0 0 8px; font-size: 30px; }}
    h2 {{ margin: 30px 0 14px; }}
    h3 {{ margin: 0 0 4px; }}
    p {{ color: var(--muted); margin: 0; }}
    main {{ padding: 24px 32px 44px; max-width: 1500px; margin: 0 auto; }}
    .cards {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 12px; }}
    .card {{ background: linear-gradient(180deg, rgba(255,255,255,.08), rgba(255,255,255,.03)); border: 1px solid rgba(255,255,255,.1); border-radius: 16px; padding: 16px; }}
    .card span {{ display: block; color: var(--muted); font-size: 13px; }}
    .card strong {{ display: block; font-size: 28px; margin-top: 6px; }}
    .toolbar {{ display: flex; flex-wrap: wrap; gap: 10px; margin: 18px 0; }}
    button, input {{
      border: 1px solid var(--line);
      border-radius: 10px;
      background: #101a28;
      color: var(--text);
      padding: 10px 12px;
      font: inherit;
    }}
    button {{ cursor: pointer; }}
    button.active {{ border-color: var(--info); box-shadow: 0 0 0 2px rgba(109,183,255,.18); }}
    input {{ min-width: 280px; flex: 1; }}
    table {{ width: 100%; border-collapse: collapse; background: rgba(16,26,40,.74); border-radius: 12px; overflow: hidden; }}
    th, td {{ border-bottom: 1px solid rgba(255,255,255,.07); padding: 10px 12px; text-align: left; vertical-align: top; }}
    th {{ background: rgba(255,255,255,.08); color: #dce8f8; font-size: 13px; }}
    tr:last-child td {{ border-bottom: 0; }}
    .pill {{ display: inline-block; border-radius: 999px; padding: 4px 9px; font-size: 12px; font-weight: 700; }}
    .pill.ok {{ color: #092014; background: var(--ok); }}
    .pill.warning {{ color: #2a1b00; background: var(--warn); }}
    .pill.error {{ color: #2c0000; background: var(--err); }}
    .pill.info {{ color: #06192d; background: var(--info); }}
    .campaign {{ background: rgba(23,34,51,.82); border: 1px solid rgba(255,255,255,.1); border-radius: 18px; padding: 18px; margin: 16px 0; }}
    details {{ margin-top: 14px; border: 1px solid rgba(255,255,255,.08); border-radius: 14px; overflow: hidden; }}
    summary {{ cursor: pointer; background: rgba(255,255,255,.06); padding: 12px 14px; font-weight: 700; }}
    summary small {{ color: var(--muted); font-weight: 400; margin-left: 8px; }}
    .muted {{ color: var(--muted); }}
    .hidden {{ display: none; }}
  </style>
</head>
<body>
  <header>
    <h1>Planner Audit Tool</h1>
    <p>Kiểm tra catalog campaign/ad set, mapping CSV và các nhánh setup nhóm quảng cáo. Tạo lúc: {esc(data["generatedAt"])}</p>
  </header>
  <main>
    <section class="cards">{cards}</section>

    <h2>Cảnh Báo</h2>
    <div class="toolbar">
      <button class="active" data-filter="all">Tất cả</button>
      <button data-filter="error">Lỗi</button>
      <button data-filter="warning">Cần kiểm tra</button>
      <button data-filter="info">Ghi chú</button>
      <input id="issueSearch" placeholder="Tìm theo campaign, bundle, nội dung...">
    </div>
    <table id="issueTable">
      <thead><tr><th>Trạng thái</th><th>Phạm vi</th><th>Nội dung</th><th>Chi tiết</th></tr></thead>
      <tbody>{issue_rows}</tbody>
    </table>

    <h2>Campaign Tổng Quan</h2>
    <table>
      <thead><tr><th>Mã campaign</th><th>Tên</th><th>Mục tiêu</th><th>Bundle hiện có</th><th>Baseline</th></tr></thead>
      <tbody>{campaign_rows}</tbody>
    </table>

    <h2>Ma Trận Flow</h2>
    <p class="muted">Mở từng campaign để kiểm tra vị trí chuyển đổi, mục tiêu hiệu quả, dataset requirement và creative type.</p>
    {''.join(matrix_sections)}
  </main>
  <script id="audit-data" type="application/json">{esc(payload)}</script>
  <script>
    const buttons = [...document.querySelectorAll('[data-filter]')];
    const rows = [...document.querySelectorAll('#issueTable tbody tr[data-status]')];
    const search = document.querySelector('#issueSearch');
    let currentFilter = 'all';

    function applyFilter() {{
      const term = (search.value || '').toLowerCase();
      rows.forEach((row) => {{
        const statusOk = currentFilter === 'all' || row.dataset.status === currentFilter;
        const termOk = !term || row.innerText.toLowerCase().includes(term);
        row.classList.toggle('hidden', !(statusOk && termOk));
      }});
    }}

    buttons.forEach((button) => {{
      button.addEventListener('click', () => {{
        currentFilter = button.dataset.filter;
        buttons.forEach((item) => item.classList.toggle('active', item === button));
        applyFilter();
      }});
    }});
    search.addEventListener('input', applyFilter);
  </script>
</body>
</html>"""


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate a local HTML audit report for planner bundles.")
    parser.add_argument("--open", action="store_true", help="Open the generated report after writing it.")
    args = parser.parse_args()

    data = audit_catalog()
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(render_report(data), encoding="utf-8")
    print(f"Wrote {REPORT_PATH}")
    print(
        f"campaigns={data['summary']['campaigns']} adsets={data['summary']['adsets']} "
        f"errors={data['summary']['errors']} warnings={data['summary']['warnings']} notes={data['summary']['notes']}"
    )
    if args.open:
        os.startfile(REPORT_PATH)  # type: ignore[attr-defined]
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
