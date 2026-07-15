#!/usr/bin/env python3
import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

from ads_core.facebook_csv import read_sample_csv, read_sample_rows, write_facebook_csv
from ads_core.mapping import DEFAULT_MAPPING, SAFE_TEMPLATE_OVERRIDE_FIELDS, VALUE_ALIASES
from ads_core.notion_api import load_env, notion_request, property_payload, property_value
from ads_core.planner_catalog import (
    PLANNER_BUNDLES_PATH,
    load_planner_bundles,
    planner_adset_bundles,
    planner_audience_presets,
    planner_campaign_bundles,
    save_planner_bundles,
)
from ads_core.settings import (
    DEFAULT_DATA_SOURCE_ID,
    DEFAULT_PARENT_PAGE_ID,
    DEFAULT_SAMPLE_CSV,
    NOTION_DATA_SOURCE_VERSION,
    NOTION_VERSION,
    STATE_FILE,
)
from ads_core.supabase_sync import (
    insert_ads_export,
    insert_sync_log,
    is_supabase_sync_configured,
    upsert_ads_plan,
)

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


AUDIENCE_PRESETS = {
    "Khách lạnh Phan Thiết": {
        "Tên nhóm QC": "Khách lạnh Phan Thiết",
        "Đối tượng tuỳ chỉnh": "",
        "Vị trí địa lý": "Phan Thiet, Bình Thuận Province, Vietnam +25km",
        "Tuổi min": 18,
        "Tuổi max": 45,
        "Giới tính": "Nữ",
        "Ngôn ngữ": "Tiếng Việt",
        "Thiết bị": "Di động",
        "Nền tảng quảng cáo": "Facebook + Messenger",
        "Vị trí Facebook": "feed, story, search, facebook_reels",
        "Vị trí Messenger": "story",
        "Mở rộng tệp": "Tắt",
        "Mở rộng nhắm chọn": "custom_audience: Off, lookalike: Off",
    },
    "Đã tương tác Page 1 năm": {
        "Tên nhóm QC": "T2 Tin nhắn | Đã tương tác Page",
        "Đối tượng tuỳ chỉnh": "120246010546010657:Đã tt với trang 1 năm",
        "Vị trí địa lý": "Phan Thiet, Bình Thuận Province, Vietnam +25km",
        "Tuổi min": 18,
        "Tuổi max": 45,
        "Giới tính": "Nữ",
        "Ngôn ngữ": "Tiếng Việt",
        "Thiết bị": "Di động",
        "Nền tảng quảng cáo": "Facebook + Messenger",
        "Vị trí Facebook": "feed, story, search, facebook_reels",
        "Vị trí Messenger": "story",
        "Mở rộng tệp": "Tắt",
        "Mở rộng nhắm chọn": "custom_audience: Off, lookalike: Off",
    },
    "Đã gửi tin nhắn 1 năm": {
        "Tên nhóm QC": "T3 Tin nhắn | Đã nhắn tin page",
        "Đối tượng tuỳ chỉnh": "120246011914780657:Đã gửi tin nhắn 1 năm",
        "Vị trí địa lý": "Phan Thiet, Bình Thuận Province, Vietnam +25km",
        "Tuổi min": 18,
        "Tuổi max": 45,
        "Giới tính": "Nữ",
        "Ngôn ngữ": "Tiếng Việt",
        "Thiết bị": "Di động",
        "Nền tảng quảng cáo": "Facebook + Messenger",
        "Vị trí Facebook": "feed, story, search, facebook_reels",
        "Vị trí Messenger": "story",
        "Mở rộng tệp": "Tắt",
        "Mở rộng nhắm chọn": "custom_audience: Off, lookalike: Off",
    },
    "T1 Video/ThruPlay | Khách lạnh": {
        "Tên nhóm QC": "T1 Video/ThruPlay | Khách lạnh Phan Thiết",
        "Vị trí chuyển đổi": "Video",
        "Mục tiêu tối ưu": "Lượt xem video",
        "Loại bài quảng cáo": "Video Page Post Ad",
        "Chiến lược giá thầu": "Cost per result goal",
        "Giới hạn giá thầu": 0.05,
        "Ngân sách trọn đời": 50,
        "Tính phí theo": "IMPRESSIONS",
        "Đối tượng tuỳ chỉnh": "",
        "Vị trí địa lý": "Phan Thiet, Bình Thuận Province, Vietnam +25km",
        "Tuổi min": 18,
        "Tuổi max": 45,
        "Giới tính": "Nữ",
        "Ngôn ngữ": "Tiếng Việt",
        "Thiết bị": "Di động",
        "Nền tảng quảng cáo": "Facebook + Messenger",
        "Vị trí Facebook": "feed, instream_video, story, search, facebook_reels, facebook_reels_overlay",
        "Vị trí Messenger": "story",
    },
    "Tăng tương tác | Khách lạnh": {
        "Tên nhóm QC": "Tăng tương tác | Khách lạnh Phan Thiết",
        "Vị trí chuyển đổi": "Bài viết",
        "Mục tiêu tối ưu": "Tương tác bài viết",
        "Loại bài quảng cáo": "Status Page Post Ad",
        "Chiến lược giá thầu": "Cost per result goal",
        "Giới hạn giá thầu": 5,
        "Ngân sách trọn đời": 50,
        "Tính phí theo": "IMPRESSIONS",
        "Đối tượng tuỳ chỉnh": "",
        "Vị trí địa lý": "Phan Thiet, Bình Thuận Province, Vietnam +25km",
        "Tuổi min": 18,
        "Tuổi max": 45,
        "Giới tính": "Nữ",
        "Ngôn ngữ": "Tiếng Việt",
        "Thiết bị": "Di động",
        "Nền tảng quảng cáo": "Facebook + Messenger",
        "Vị trí Facebook": "feed, story, search, facebook_reels",
        "Vị trí Messenger": "story",
    },
    "Tăng tương tác | Đã tương tác Page": {
        "Tên nhóm QC": "Tăng tương tác | Đã tương tác page",
        "Vị trí chuyển đổi": "Bài viết",
        "Mục tiêu tối ưu": "Tương tác bài viết",
        "Loại bài quảng cáo": "Status Page Post Ad",
        "Chiến lược giá thầu": "Cost per result goal",
        "Giới hạn giá thầu": 0.05,
        "Ngân sách trọn đời": 50,
        "Tính phí theo": "IMPRESSIONS",
        "Đối tượng tuỳ chỉnh": "120246010546010657:Đã tt với trang 1 năm",
        "Vị trí địa lý": "Phan Thiet, Bình Thuận Province, Vietnam +25km",
        "Tuổi min": 18,
        "Tuổi max": 45,
        "Giới tính": "Nữ",
        "Ngôn ngữ": "Tiếng Việt",
        "Thiết bị": "Di động",
        "Nền tảng quảng cáo": "Facebook + Messenger",
        "Vị trí Facebook": "feed, story, search, facebook_reels",
        "Vị trí Messenger": "story",
    },
    "T3 Tin nhắn | Đã nhắn tin Page": {
        "Tên nhóm QC": "T3 Tin nhắn | Đã nhắn tin page",
        "Vị trí chuyển đổi": "Đích đến của tin nhắn",
        "Mục tiêu tối ưu": "Tin nhắn",
        "Loại bài quảng cáo": "Video Page Post Ad",
        "Chiến lược giá thầu": "Giới hạn giá thầu",
        "Giới hạn giá thầu": 5,
        "Ngân sách trọn đời": 50,
        "Tính phí theo": "IMPRESSIONS",
        "Đối tượng tuỳ chỉnh": "120246011914780657:Đã gửi tin nhắn 1 năm",
        "Vị trí địa lý": "Phan Thiet, Bình Thuận Province, Vietnam +25km",
        "Tuổi min": 18,
        "Tuổi max": 45,
        "Giới tính": "Nữ",
        "Ngôn ngữ": "Tiếng Việt",
        "Thiết bị": "Di động",
        "Nền tảng quảng cáo": "Facebook + Messenger",
        "Vị trí Facebook": "feed, story, search, facebook_reels",
        "Vị trí Messenger": "story",
    },
}

AD_SET_NAME_OPTIONS = [
    "T2 Tin nhắn | Đã tương tác Page",
    "T3 Tin nhắn | Đã nhắn tin page",
    "T1 Video/ThruPlay | Khách lạnh Phan Thiết",
    "Tăng tương tác | Khách lạnh Phan Thiết",
    "Tăng tương tác | Đã tương tác page",
    "Khách lạnh Phan Thiết",
]

DEFAULTS = {
    "Ad Status": "ACTIVE",
    "Ad Set Run Status": "ACTIVE",
    "Campaign Status": "ACTIVE",
    "Additional Custom Tracking Specs": "[]",
    "Optimize text per person": "No",
    "Use Page as Actor": "No",
    "Video Retargeting": "No",
    "Buy With Integration Partner": "NONE",
    "Buy With Prime Type": "NONE",
    "Buying Type": "AUCTION",
    "Campaign High Demand Periods": "[]",
    "Is Budget Scheduling Enabled For Campaign": "No",
    "New Objective": "Yes",
    "Ad Set Bid Strategy": "Bid cap",
    "Ad Set Daily Budget": "0",
    "Ad Set Lifetime Budget": "50",
    "Bid Amount": "5",
    "Destination Type": "MESSENGER",
    "Optimization Goal": "CONVERSATIONS",
    "Billing Event": "IMPRESSIONS",
    "Cities": "Phan Thiet, Bình Thuận Province, Vietnam +25km",
    "Age Min": "18",
    "Age Max": "45",
    "Gender": "Women",
    "Locales": "Vietnamese",
    "Device Platforms": "mobile",
    "Publisher Platforms": "facebook, messenger",
    "Facebook Positions": "feed, story, search, facebook_reels",
    "Messenger Positions": "story",
    "Targeting Relaxation": "custom_audience: Off, lookalike: Off",
    "Use Accelerated Delivery": "No",
}

DRAFT_DEFAULT_VALUES = {
    "Trạng thái": "Not started",
    "Mẫu đối tượng": "Đã tương tác Page 1 năm",
    "Vị trí chuyển đổi": "Đích đến của tin nhắn",
    "Đích đến tin nhắn": "Đích đến thủ công",
    "Trang Facebook": "Nhà thuốc Khải Hoàn Skincare - Chăm sóc da chuẩn y khoa Phan Thiết",
    "Chiến lược giá thầu": "Giới hạn giá thầu",
    "Giới hạn giá thầu": 5,
    "Loại ngân sách": "Lifetime",
    "Ngân sách trọn đời": 50,
    "Ngân sách/ngày": 0,
    "Mục tiêu tối ưu": "Tin nhắn",
    "Tính phí theo": "IMPRESSIONS",
    "Đối tượng tuỳ chỉnh": "120246010546010657:Đã tt với trang 1 năm",
    "Vị trí địa lý": "Phan Thiet, Bình Thuận Province, Vietnam +25km",
    "Tuổi min": 18,
    "Tuổi max": 45,
    "Giới tính": "Nữ",
    "Ngôn ngữ": "Tiếng Việt",
    "Thiết bị": "Di động",
    "Nền tảng quảng cáo": "Facebook + Messenger",
    "Vị trí Facebook": "feed, story, search, facebook_reels",
    "Vị trí Messenger": "story",
    "Mở rộng tệp": "Tắt",
    "Mở rộng nhắm chọn": "custom_audience: Off, lookalike: Off",
    "Nút CTA": "MESSAGE_PAGE",
    "Loại bài quảng cáo": "Video Page Post Ad",
    "Tên nhóm QC": "T2 Tin nhắn | Đã tương tác Page",
    "Tên chiến dịch": "Chiến dịch Tin nhắn Khải Hoàn",
    "Đã xuất": False,
}

DEFAULT_READY_STATUS_NAMES = ["Ready", "To-do", "Not started"]
DEFAULT_EXPORTED_STATUS_NAMES = ["Done", "Complete", "Exported"]

NOTION_PROPERTIES = {
    "Tên chiến dịch / bài ads": {"title": {}},
    "Tên quảng cáo": {"rich_text": {}},
    "Trạng thái": {
        "select": {
            "options": [
                {"name": "Draft", "color": "gray"},
                {"name": "Ready", "color": "green"},
                {"name": "Exported", "color": "blue"},
            ]
        }
    },
    "Nội dung": {"rich_text": {}},
    "Facebook Post URL": {"url": {}},
    "Link bài viết": {"url": {}},
    "Story ID": {"rich_text": {}},
    "ID Story": {"rich_text": {}},
    "Video ID": {"rich_text": {}},
    "ID Video": {"rich_text": {}},
    "Link URL": {"url": {}},
    "Link đích": {"url": {}},
    "CTA": {
        "select": {
            "options": [
                {"name": "MESSAGE_PAGE", "color": "green"},
                {"name": "LEARN_MORE", "color": "blue"},
                {"name": "BOOK_TRAVEL", "color": "purple"},
                {"name": "NO_BUTTON", "color": "gray"},
            ]
        }
    },
    "Nút CTA": {
        "select": {
            "options": [
                {"name": "MESSAGE_PAGE", "color": "green"},
                {"name": "LEARN_MORE", "color": "blue"},
                {"name": "BOOK_TRAVEL", "color": "purple"},
                {"name": "NO_BUTTON", "color": "gray"},
            ]
        }
    },
    "Tiêu đề link": {"rich_text": {}},
    "Mô tả link": {"rich_text": {}},
    "Creative Type": {
        "select": {
            "options": [
                {"name": "Video Page Post Ad", "color": "red"},
                {"name": "Photo Page Post Ad", "color": "yellow"},
                {"name": "Status Page Post Ad", "color": "gray"},
                {"name": "Lead Ad", "color": "green"},
                {"name": "Website Click Ad", "color": "blue"},
                {"name": "Message Click Ad", "color": "purple"},
                {"name": "Call Ad", "color": "orange"},
                {"name": "Page Like Ad", "color": "pink"},
            ]
        }
    },
    "Loại bài quảng cáo": {"rich_text": {}},
    "Campaign Name": {"rich_text": {}},
    "Tên chiến dịch": {"rich_text": {}},
    "Mục tiêu chiến dịch": {"rich_text": {}},
    "Kiểm soát tần suất": {"rich_text": {}},
    "Tập dữ liệu": {"rich_text": {}},
    "Mô hình ghi nhận": {"rich_text": {}},
    "Mẫu đối tượng": {"rich_text": {}},
    "Ad Set Name": {"rich_text": {}},
    "Tên nhóm QC": {"rich_text": {}},
    "Vị trí chuyển đổi": {"rich_text": {}},
    "Loại tương tác": {"rich_text": {}},
    "Đích đến tin nhắn": {"rich_text": {}},
    "Ứng dụng nhắn tin": {"rich_text": {}},
    "Trang Facebook": {"rich_text": {}},
    "Mục tiêu tối ưu": {"rich_text": {}},
    "Chiến lược giá thầu": {"rich_text": {}},
    "Loại ngân sách": {"rich_text": {}},
    "Lifetime Budget": {"number": {"format": "number"}},
    "Ngân sách trọn đời": {"number": {"format": "number"}},
    "Ngân sách/ngày": {"number": {"format": "number"}},
    "Bid Amount": {"rich_text": {}},
    "Giới hạn giá thầu": {"number": {"format": "number"}},
    "Tính phí theo": {"rich_text": {}},
    "Đối tượng tuỳ chỉnh": {"rich_text": {}},
    "Vị trí địa lý": {"rich_text": {}},
    "Tuổi min": {"number": {"format": "number"}},
    "Tuổi max": {"number": {"format": "number"}},
    "Giới tính": {"rich_text": {}},
    "Ngôn ngữ": {"rich_text": {}},
    "Thiết bị": {"rich_text": {}},
    "Nền tảng quảng cáo": {"rich_text": {}},
    "Vị trí Facebook": {"rich_text": {}},
    "Vị trí Messenger": {"rich_text": {}},
    "Mở rộng tệp": {"rich_text": {}},
    "Mở rộng nhắm chọn": {"rich_text": {}},
    "Start Time": {"date": {}},
    "Stop Time": {"date": {}},
    "Exported": {"checkbox": {}},
    "Đã xuất": {"checkbox": {}},
    "Ghi chú": {"rich_text": {}},
}


def telegram_request(method_name, payload=None):
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not bot_token:
        return None
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        f"https://api.telegram.org/bot{bot_token}/{method_name}",
        data=data,
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=max(20, int((payload or {}).get("timeout", 0)) + 10)) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        print(f"Telegram API Error {exc.code}: {detail}", file=sys.stderr)
        try:
            return json.loads(detail)
        except Exception:
            return {"ok": False, "description": f"HTTP Error {exc.code}: {exc.reason}"}
    except Exception as exc:
        print(f"Telegram Request Error: {exc}", file=sys.stderr)
        return {"ok": False, "description": str(exc)}


def telegram_delete_webhook():
    if not os.environ.get("TELEGRAM_BOT_TOKEN"):
        return False
    result = telegram_request("deleteWebhook")
    return bool(result and result.get("ok"))


def telegram_send(message, reply_markup=None):
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not os.environ.get("TELEGRAM_BOT_TOKEN") or not chat_id:
        return False
    payload = {"chat_id": chat_id, "text": message}
    if reply_markup:
        payload["reply_markup"] = reply_markup
    result = telegram_request("sendMessage", payload)
    return result.get("result") if result and result.get("ok") else False


def telegram_send_document(file_path, caption=""):
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not bot_token or not chat_id:
        return False
    path = Path(file_path)
    if not path.exists():
        return False
    file_name = path.name
    file_bytes = path.read_bytes()
    boundary = "----WebKitFormBoundary7MA4YWxkTrZu0gW"
    parts = []
    parts.append(f"--{boundary}")
    parts.append('Content-Disposition: form-data; name="chat_id"')
    parts.append("")
    parts.append(str(chat_id))
    if caption:
        parts.append(f"--{boundary}")
        parts.append('Content-Disposition: form-data; name="caption"')
        parts.append("")
        parts.append(caption)
    parts.append(f"--{boundary}")
    parts.append(f'Content-Disposition: form-data; name="document"; filename="{file_name}"')
    parts.append('Content-Type: application/octet-stream')
    parts.append("")
    body_header = "\r\n".join(parts).encode("utf-8") + b"\r\n"
    body_footer = b"\r\n" + f"--{boundary}--\r\n".encode("utf-8")
    body = body_header + file_bytes + body_footer
    request = urllib.request.Request(
        f"https://api.telegram.org/bot{bot_token}/sendDocument",
        data=body,
        method="POST",
        headers={
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "Content-Length": str(len(body))
        }
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            result = json.loads(response.read().decode("utf-8"))
            return bool(result and result.get("ok"))
    except Exception as e:
        print(f"Lỗi gửi document Telegram: {e}", file=sys.stderr)
        return False


def telegram_get_updates(offset=None, timeout=20):
    payload = {"timeout": timeout, "allowed_updates": ["callback_query"]}
    if offset is not None:
        payload["offset"] = offset
    result = telegram_request("getUpdates", payload)
    return result.get("result", []) if result and result.get("ok") else []


def telegram_answer_callback(callback_query_id, text=""):
    if not callback_query_id:
        return False
    payload = {"callback_query_id": callback_query_id}
    if text:
        payload["text"] = text
    result = telegram_request("answerCallbackQuery", payload)
    return bool(result and result.get("ok"))


def telegram_edit_message(chat_id, message_id, text, reply_markup=None):
    payload = {"chat_id": chat_id, "message_id": message_id, "text": text}
    if reply_markup is not None:
        payload["reply_markup"] = reply_markup
    result = telegram_request("editMessageText", payload)
    return bool(result and result.get("ok"))


def validate_notion_schema_for_values(props_schema, values, context="planner"):
    missing = sorted(
        name
        for name, value in values.items()
        if name not in props_schema and value not in ("", None)
    )
    if not missing:
        return
    preview = ", ".join(missing[:30])
    extra = "" if len(missing) <= 30 else f" ... và {len(missing) - 30} trường khác"
    raise RuntimeError(
        "Database Notion hiện thiếu cột để ghi đủ dữ liệu "
        f"{context}: {preview}{extra}. "
        "Hãy thêm các cột này vào database hiện tại hoặc tạo database mẫu mới bằng lệnh "
        "create-notion-template rồi chạy lại."
    )


def resolve_facebook_post_metadata(url):
    metadata = {}
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0",
            "Accept": "text/html,application/xhtml+xml",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            html = response.read().decode("utf-8", errors="replace")
    except Exception:
        return metadata

    patterns = {
        "post_id": [
            r'"top_level_post_id":"(\d+)"',
            r'"post_id":"(\d+)"',
            r'"subscription_target_id":"(\d+)"',
        ],
        "page_id": [
            r'\\"page_id\\":\\"(\d+)\\"',
            r'"page_id":"(\d+)"',
            r'\\"content_owner_id_new\\":\\"(\d+)\\"',
            r'"content_owner_id_new":"(\d+)"',
            r'"owning_profile_id":"(\d+)"',
        ],
        "photo_id": [r'\\"photo_id\\":\\"(\d+)\\"', r'"photo_id":"(\d+)"'],
        "video_id": [
            r'\\"video_id\\":\\"(\d+)\\"',
            r'"video_id":"(\d+)"',
            r'"associated_video":\{"id":"(\d+)"',
        ],
        "attachment_style": [
            r'\\"story_attachment_style\\":\\"([^"\\]+)\\"',
            r'"story_attachment_style":"([^"]+)"',
        ],
    }
    for key, regexes in patterns.items():
        for pattern in regexes:
            match = re.search(pattern, html)
            if match:
                metadata[key] = match.group(1)
                break

    if metadata.get("post_id"):
        metadata["story_id"] = f"s:{metadata['post_id']}"
    if metadata.get("video_id"):
        metadata["video_id"] = f"v:{metadata['video_id']}"
        metadata["creative_type"] = "Video Page Post Ad"
    elif metadata.get("photo_id") or metadata.get("attachment_style") == "photo":
        metadata["creative_type"] = "Photo Page Post Ad"
    elif metadata.get("post_id"):
        metadata["creative_type"] = "Status Page Post Ad"
    if metadata.get("page_id"):
        metadata["link_object_id"] = f"o:{metadata['page_id']}"
    return metadata


def parse_facebook_post_link(url, resolve=False):
    parsed = urlparse(url.strip())
    path_parts = [part for part in parsed.path.split("/") if part]
    query = parse_qs(parsed.query)
    clean_query = {}
    for key in ("story_fbid", "fbid", "id", "v"):
        if key in query:
            clean_query[key] = query[key][0]
    clean_url = urlunparse(
        (
            parsed.scheme or "https",
            parsed.netloc,
            parsed.path.rstrip("/"),
            "",
            urlencode(clean_query),
            "",
        )
    )
    info = {
        "url": clean_url,
        "post_id": "",
        "story_id": "",
        "video_id": "",
        "creative_type": "",
        "title": "",
    }

    if "story_fbid" in query:
        info["post_id"] = query["story_fbid"][0]
        info["story_id"] = f"s:{info['post_id']}"
    if "fbid" in query:
        info["post_id"] = query["fbid"][0]
        info["story_id"] = f"s:{info['post_id']}"
    if "v" in query:
        info["video_id"] = f"v:{query['v'][0]}"
        info["creative_type"] = "Video Page Post Ad"

    for index, part in enumerate(path_parts):
        if part in ("reel", "videos", "watch") and index + 1 < len(path_parts):
            raw_id = path_parts[index + 1]
            if raw_id.isdigit():
                info["video_id"] = f"v:{raw_id}"
                info["creative_type"] = "Video Page Post Ad"
                info["post_id"] = raw_id
        if part in ("posts", "photos") and index + 1 < len(path_parts):
            raw_id = path_parts[index + 1]
            info["post_id"] = raw_id
            if raw_id.isdigit():
                info["story_id"] = f"s:{raw_id}"
            if part == "posts" and not info["video_id"]:
                info["creative_type"] = "Status Page Post Ad"

    if not info["creative_type"]:
        info["creative_type"] = "Status Page Post Ad" if info["story_id"] else "Video Page Post Ad"

    identifier = info["post_id"] or info["video_id"].replace("v:", "") or datetime.now().strftime("%Y%m%d%H%M")
    info["title"] = f"Bài quảng cáo Facebook {identifier}"
    if resolve and ("/posts/" in parsed.path or "pfbid" in url):
        metadata = resolve_facebook_post_metadata(clean_url)
        info.update({key: value for key, value in metadata.items() if value})
    return info


def create_notion_ad_draft(data_source_id, facebook_url, ad_name=None):
    schema = get_source_schema(data_source_id)
    props_schema = schema.get("properties", {})
    link_info = parse_facebook_post_link(facebook_url, resolve=True)
    values = dict(DRAFT_DEFAULT_VALUES)
    values.update(
        {
            "Tên chiến dịch / bài ads": ad_name or link_info["title"],
            "Link bài viết": link_info["url"],
            "ID Story": link_info["story_id"],
            "ID Video": link_info["video_id"],
            "Loại bài quảng cáo": link_info["creative_type"],
            "Ghi chú": "Nháp tạo tự động từ link Facebook. Quản lý kiểm tra nội dung trước khi export.",
        }
    )

    page_props = {}
    for name, value in values.items():
        if name not in props_schema or value in ("", None):
            continue
        payload = property_payload(props_schema[name], value)
        if payload:
            page_props[name] = payload

    payload = {
        "parent": {"type": "data_source_id", "data_source_id": data_source_id},
        "properties": page_props,
    }
    try:
        return notion_request("POST", "/pages", payload, notion_version=NOTION_DATA_SOURCE_VERSION)
    except RuntimeError as exc:
        if "data_source" not in str(exc) and "parent" not in str(exc):
            raise
        payload["parent"] = {"type": "database_id", "database_id": data_source_id}
        return notion_request("POST", "/pages", payload)


def create_notion_ad_draft_with_overrides(
    data_source_id,
    facebook_url,
    ad_name=None,
    overrides=None,
    strict_schema=False,
):
    schema = get_source_schema(data_source_id)
    props_schema = schema.get("properties", {})
    link_info = parse_facebook_post_link(facebook_url, resolve=True)
    values = dict(DRAFT_DEFAULT_VALUES)
    values.update(
        {
            "Tên chiến dịch / bài ads": ad_name or link_info["title"],
            "Link bài viết": link_info["url"],
            "ID Story": link_info["story_id"],
            "ID Video": link_info["video_id"],
            "Loại bài quảng cáo": link_info["creative_type"],
            "Ghi chú": "Nháp tạo tự động từ link Facebook. Quản lý kiểm tra nội dung trước khi export.",
        }
    )
    if overrides:
        values.update({key: value for key, value in overrides.items() if value not in (None, "")})
        if overrides.get("Tên chiến dịch / bài ads"):
            values["Tên chiến dịch / bài ads"] = overrides["Tên chiến dịch / bài ads"]

    if strict_schema:
        validate_notion_schema_for_values(props_schema, values, context=ad_name or "planner")

    page_props = {}
    for name, value in values.items():
        if name not in props_schema or value in ("", None):
            continue
        payload = property_payload(props_schema[name], value)
        if payload:
            page_props[name] = payload

    payload = {
        "parent": {"type": "data_source_id", "data_source_id": data_source_id},
        "properties": page_props,
    }
    try:
        return notion_request("POST", "/pages", payload, notion_version=NOTION_DATA_SOURCE_VERSION)
    except RuntimeError as exc:
        if "data_source" not in str(exc) and "parent" not in str(exc):
            raise
        payload["parent"] = {"type": "database_id", "database_id": data_source_id}
        return notion_request("POST", "/pages", payload)


def create_notion_ad_drafts_from_bundles(
    data_source_id,
    facebook_url,
    campaign_bundle_code,
    adset_bundle_codes,
    audience_preset_codes=None,
    dataset_preset_code=None,
    budget_preset_code=None,
    custom_budget_values=None,
    placement_preset_code=None,
    creative_mode="existing_post",
    ad_name=None,
):
    catalog = load_planner_bundles()
    campaign = next(
        (item for item in catalog.get("campaignBundles", []) if item.get("code") == campaign_bundle_code),
        None,
    )
    if not campaign:
        raise RuntimeError(f"Không tìm thấy campaign bundle: {campaign_bundle_code}")
    adset_lookup = {item.get("code"): item for item in catalog.get("adSetBundles", [])}
    audience_lookup = {item.get("code"): item for item in catalog.get("audiencePresets", [])}
    dataset_lookup = {item.get("code"): item for item in catalog.get("datasetPresets", [])}
    budget_lookup = {item.get("code"): item for item in catalog.get("budgetPresets", [])}
    placement_lookup = {item.get("code"): item for item in catalog.get("placementPresets", [])}
    dataset_preset = dataset_lookup.get(dataset_preset_code) if dataset_preset_code else None
    budget_preset = budget_lookup.get(budget_preset_code) if budget_preset_code else None
    placement_preset = placement_lookup.get(placement_preset_code) if placement_preset_code else None
    if dataset_preset_code and not dataset_preset:
        raise RuntimeError(f"Không tìm thấy dataset preset: {dataset_preset_code}")
    if budget_preset_code and not budget_preset:
        raise RuntimeError(f"Không tìm thấy budget preset: {budget_preset_code}")
    if placement_preset_code and not placement_preset:
        raise RuntimeError(f"Không tìm thấy placement preset: {placement_preset_code}")
    custom_budget_values = custom_budget_values or {}
    results = []
    selected_audience_codes = audience_preset_codes or [None]
    for adset_code in adset_bundle_codes:
        adset_bundle = adset_lookup.get(adset_code)
        if not adset_bundle:
            raise RuntimeError(f"Không tìm thấy ad set bundle: {adset_code}")
        for audience_code in selected_audience_codes:
            audience_preset = audience_lookup.get(audience_code) if audience_code else None
            if audience_code and not audience_preset:
                raise RuntimeError(f"Không tìm thấy audience preset: {audience_code}")
            overrides = {}
            overrides.update(campaign.get("notionValues", {}))
            overrides.update(adset_bundle.get("notionValues", {}))
            if audience_preset:
                overrides.update(audience_preset.get("notionValues", {}))
            if dataset_preset:
                overrides.update(dataset_preset.get("notionValues", {}))
            if budget_preset:
                overrides.update(budget_preset.get("notionValues", {}))
            if custom_budget_values:
                overrides.update(custom_budget_values)
            if placement_preset:
                overrides.update(placement_preset.get("notionValues", {}))
            note_lines = [
                f"Campaign bundle: {campaign.get('code')} - {campaign.get('name')}",
                f"Ad set bundle: {adset_bundle.get('code')} - {adset_bundle.get('name')}",
                f"Creative mode: {creative_mode}",
                f"Conversion location: {adset_bundle.get('conversionLocation', '')}",
                f"Interaction type: {adset_bundle.get('interactionType', '')}",
                f"Performance goal: {adset_bundle.get('performanceGoal', '')}",
            ]
            if audience_preset:
                note_lines.append(f"Audience preset: {audience_preset.get('code')} - {audience_preset.get('name')}")
            if dataset_preset:
                note_lines.append(f"Dataset preset: {dataset_preset.get('code')} - {dataset_preset.get('name')}")
            if budget_preset:
                note_lines.append(f"Budget preset: {budget_preset.get('code')} - {budget_preset.get('name')}")
            if custom_budget_values:
                custom_budget_note = ", ".join(
                    f"{key}: {value}" for key, value in custom_budget_values.items() if value not in ("", None)
                )
                if custom_budget_note:
                    note_lines.append(f"Custom budget: {custom_budget_note}")
            if placement_preset:
                note_lines.append(f"Placement preset: {placement_preset.get('code')} - {placement_preset.get('name')}")
            existing_note = overrides.get("Ghi chú") or DRAFT_DEFAULT_VALUES.get("Ghi chú", "")
            if existing_note:
                note_lines.insert(0, existing_note)
            overrides["Ghi chú"] = "\n".join(line for line in note_lines if line)
            bundle_ad_name = ad_name
            if not bundle_ad_name:
                name_parts = [campaign.get("name"), adset_bundle.get("name")]
                if audience_preset:
                    name_parts.append(audience_preset.get("name"))
                bundle_ad_name = " | ".join(part for part in name_parts if part)
            results.append(
                create_notion_ad_draft_with_overrides(
                    data_source_id,
                    facebook_url,
                    ad_name=bundle_ad_name,
                    overrides=overrides,
                    strict_schema=True,
                )
            )
    return results

def notion_page_to_values(page):
    props = page.get("properties", {})
    return {name: property_value(prop) for name, prop in props.items()}


def facebook_datetime(notion_date):
    if not notion_date:
        return ""
    raw = notion_date.replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(raw)
    except ValueError:
        return notion_date
    hour = dt.hour % 12 or 12
    suffix = "am" if dt.hour < 12 else "pm"
    return f"{dt.month:02d}/{dt.day:02d}/{dt.year} {hour}:{dt.minute:02d}:{dt.second:02d} {suffix}"


def load_mapping(path):
    mapping = dict(DEFAULT_MAPPING)
    if path:
        custom = json.loads(Path(path).read_text(encoding="utf-8"))
        mapping.update(custom)
    return mapping


def normalize_mapped_value(notion_name, value):
    if value in (None, ""):
        return value
    if isinstance(value, float):
        return str(value).replace(".", ",")
    text = str(value).strip()
    if notion_name in ("Facebook Post URL", "Link bài viết"):
        return parse_facebook_post_link(text)["url"]
    if notion_name == "Kiểm soát tần suất":
        match = re.search(r"(\d+)\s*lần\s*/\s*(\d+)\s*ngày", text, flags=re.IGNORECASE)
        if match:
            max_frequency, interval_days = match.groups()
            return json.dumps(
                [
                    {
                        "event": "IMPRESSIONS",
                        "interval_days": int(interval_days),
                        "max_frequency": int(max_frequency),
                    }
                ],
                separators=(",", ":"),
            )
    alias = VALUE_ALIASES.get(notion_name, {})
    return alias.get(text, text)


def get_source_schema(data_source_or_database_id):
    try:
        return notion_request(
            "GET",
            f"/data_sources/{data_source_or_database_id}",
            notion_version=NOTION_DATA_SOURCE_VERSION,
        )
    except RuntimeError:
        return notion_request("GET", f"/databases/{data_source_or_database_id}")


def configured_names(env_key, defaults):
    raw = os.environ.get(env_key, "")
    names = [item.strip() for item in raw.split(",") if item.strip()]
    return names or defaults


def available_option_names(prop):
    prop_type = prop.get("type")
    config = prop.get(prop_type, {}) if prop_type else {}
    if prop_type == "status":
        options = []
        for group in config.get("groups", []):
            options.extend(group.get("option_ids", []))
        by_id = {item.get("id"): item.get("name") for item in config.get("options", [])}
        names = [by_id.get(option_id) for option_id in options if by_id.get(option_id)]
        if names:
            return names
    return [item.get("name") for item in config.get("options", []) if item.get("name")]


def query_ready_pages(data_source_or_database_id, include_exported=False, ready_names=None):
    schema = get_source_schema(data_source_or_database_id)
    properties = schema.get("properties", {})
    filters = []
    status_prop = properties.get("Trạng thái")
    if status_prop:
        status_type = status_prop.get("type")
        ready_names = ready_names or configured_names("READY_STATUS_NAMES", DEFAULT_READY_STATUS_NAMES)
        available = available_option_names(status_prop)
        if available:
            ready_names = [name for name in ready_names if name in available]
        status_filters = []
        for name in ready_names:
            if status_type == "status":
                status_filters.append({"property": "Trạng thái", "status": {"equals": name}})
            elif status_type == "select":
                status_filters.append({"property": "Trạng thái", "select": {"equals": name}})
        if len(status_filters) == 1:
            filters.append(status_filters[0])
        elif status_filters:
            filters.append({"or": status_filters})
    exported_prop_name = "Đã xuất" if properties.get("Đã xuất", {}).get("type") == "checkbox" else "Exported"
    if not include_exported and properties.get(exported_prop_name, {}).get("type") == "checkbox":
        filters.append({"property": exported_prop_name, "checkbox": {"equals": False}})
    payload = {"filter": {"and": filters}, "page_size": 100}
    if not filters:
        payload = {"page_size": 100}
    pages = []
    while True:
        try:
            result = notion_request(
                "POST",
                f"/data_sources/{data_source_or_database_id}/query",
                payload,
                notion_version=NOTION_DATA_SOURCE_VERSION,
            )
        except RuntimeError as exc:
            if "Could not find data source" not in str(exc) and "Invalid request URL" not in str(exc):
                raise
            result = notion_request("POST", f"/databases/{data_source_or_database_id}/query", payload)
        pages.extend(result.get("results", []))
        if not result.get("has_more"):
            break
        payload["start_cursor"] = result.get("next_cursor")
    return pages


def choose_template_row(values, sample_rows, fallback_row):
    wanted_adset = values.get("Tên nhóm QC") or values.get("Ad Set Name")
    preset = AUDIENCE_PRESETS.get(values.get("Mẫu đối tượng", ""))
    if preset:
        wanted_adset = values.get("Tên nhóm QC") or preset.get("Tên nhóm QC") or wanted_adset
    if wanted_adset:
        for row in sample_rows:
            if row.get("Ad Set Name") == wanted_adset:
                return dict(row), True
    return dict(fallback_row), False


def build_facebook_rows(pages, headers, template_row, mapping, sample_rows=None):
    output_rows = []
    missing_columns = sorted({col for col in mapping.values() if col not in headers})
    if missing_columns:
        raise RuntimeError("File mẫu thiếu cột: " + ", ".join(missing_columns))

    for page in pages:
        notion_values = notion_page_to_values(page)
        preset = AUDIENCE_PRESETS.get(notion_values.get("Mẫu đối tượng", ""))
        base_row, matched_template = choose_template_row(notion_values, sample_rows or [], template_row)
        if preset and not matched_template:
            values = dict(preset)
            values.update({key: value for key, value in notion_values.items() if value not in (None, "")})
        else:
            values = notion_values
        row = {header: base_row.get(header, "") for header in headers}
        for key, value in DEFAULTS.items():
            if key in headers and (not matched_template or not row.get(key)):
                row[key] = value
        for notion_name, facebook_column in mapping.items():
            if matched_template and notion_name not in SAFE_TEMPLATE_OVERRIDE_FIELDS:
                continue
            value = values.get(notion_name)
            if value not in (None, ""):
                row[facebook_column] = str(normalize_mapped_value(notion_name, value))
            elif preset and notion_name in preset:
                row[facebook_column] = ""
        apply_campaign_objective_fallback(row, values)
        clean_stale_creative_fields(row, values)
        if values.get("Start Time"):
            row["Ad Set Time Start"] = facebook_datetime(values["Start Time"])
            row["Campaign Start Time"] = facebook_datetime(values["Start Time"])
        if values.get("Ngày bắt đầu"):
            row["Ad Set Time Start"] = facebook_datetime(values["Ngày bắt đầu"])
            row["Campaign Start Time"] = facebook_datetime(values["Ngày bắt đầu"])
        if values.get("Stop Time"):
            row["Ad Set Time Stop"] = facebook_datetime(values["Stop Time"])
            row["Campaign Stop Time"] = facebook_datetime(values["Stop Time"])
        if values.get("Ngày kết thúc"):
            row["Ad Set Time Stop"] = facebook_datetime(values["Ngày kết thúc"])
            row["Campaign Stop Time"] = facebook_datetime(values["Ngày kết thúc"])
        output_rows.append(row)
    return output_rows


def apply_campaign_objective_fallback(row, values):
    if "Campaign Objective" not in row:
        return
    campaign_objective = values.get("Mục tiêu chiến dịch")
    campaign_name = values.get("Tên chiến dịch") or values.get("Campaign Name") or ""
    if campaign_objective:
        row["Campaign Objective"] = normalize_mapped_value("Mục tiêu chiến dịch", campaign_objective)
        return
    campaign_name_text = str(campaign_name).lower()
    if "traffic" in campaign_name_text or "lưu lượng" in campaign_name_text:
        row["Campaign Objective"] = "Outcome Traffic"
    elif "nhận biết" in campaign_name_text or "awareness" in campaign_name_text:
        row["Campaign Objective"] = "Outcome Awareness"
    else:
        row["Campaign Objective"] = "Outcome Engagement"


def clean_stale_creative_fields(row, values):
    post_link = values.get("Link bài viết") or values.get("Facebook Post URL") or ""
    has_new_link = bool(str(post_link).strip())
    if not has_new_link:
        return

    explicit_story = values.get("ID Story") or values.get("Story ID")
    explicit_video = values.get("ID Video") or values.get("Video ID")
    link_info = parse_facebook_post_link(str(post_link), resolve=True)

    if not explicit_story and link_info.get("story_id"):
        explicit_story = link_info["story_id"]
        if "Story ID" in row:
            row["Story ID"] = explicit_story
    if not explicit_video and link_info.get("video_id"):
        explicit_video = link_info["video_id"]
        if "Video ID" in row:
            row["Video ID"] = explicit_video
    if link_info.get("creative_type") and "Creative Type" in row:
        row["Creative Type"] = link_info["creative_type"]
    if link_info.get("link_object_id") and "Link Object ID" in row:
        row["Link Object ID"] = link_info["link_object_id"]

    if not explicit_story:
        for column in ("Story ID",):
            if column in row:
                row[column] = ""
    if not explicit_video:
        for column in ("Video ID", "Video File Name", "Video Thumbnail URL"):
            if column in row:
                row[column] = ""

    text_fallbacks = {
        "Body": values.get("Nội dung"),
        "Title": values.get("Tiêu đề link"),
        "Link Description": values.get("Mô tả link"),
    }
    for column, provided in text_fallbacks.items():
        if column in row and not provided:
            row[column] = ""
    for column in (
        "Display Link",
        "Image File Name",
        "Image Hash",
        "Preview Link",
        "Instagram Platform Image Hash",
        "Instagram Platform Image URL",
        "Product 1 - Image Hash",
        "Product 1 - Video ID",
    ):
        if column in row:
            row[column] = ""

    # Avoid importing media from the cloned template row when the new post URL
    # cannot be converted to a numeric Story ID / Video ID.
    if not explicit_story and not explicit_video:
        if "/posts/" in str(post_link):
            row["Creative Type"] = "Status Page Post Ad"
        for column in (
            "Link Object ID",
        ):
            if column in row:
                row[column] = ""


def update_exported(page_id, page_properties=None):
    page_properties = page_properties or {}
    properties = {}
    exported_prop_name = "Đã xuất" if page_properties.get("Đã xuất", {}).get("type") == "checkbox" else "Exported"
    exported_at_prop_name = (
        "Thời gian xuất" if page_properties.get("Thời gian xuất", {}).get("type") == "date" else "Exported At"
    )
    if page_properties.get(exported_prop_name, {}).get("type") == "checkbox":
        properties[exported_prop_name] = {"checkbox": True}
    if page_properties.get(exported_at_prop_name, {}).get("type") == "date":
        properties[exported_at_prop_name] = {"date": {"start": datetime.now().isoformat(timespec="seconds")}}
    status_type = page_properties.get("Trạng thái", {}).get("type")
    exported_defaults = DEFAULT_EXPORTED_STATUS_NAMES if status_type == "status" else ["Exported", "Done", "Complete"]
    exported_names = configured_names("EXPORTED_STATUS_NAMES", exported_defaults)
    available = available_option_names(page_properties.get("Trạng thái", {}))
    exported_name = next((name for name in exported_names if not available or name in available), None)
    if status_type == "status":
        if exported_name:
            properties["Trạng thái"] = {"status": {"name": exported_name}}
    elif status_type == "select":
        if exported_name:
            properties["Trạng thái"] = {"select": {"name": exported_name}}
    if not properties:
        return
    payload = {"properties": properties}
    notion_request("PATCH", f"/pages/{page_id}", payload)


def update_page_status_by_id(page_id, status_name, fallback_status_names=None, note_content=None):
    try:
        page = notion_request("GET", f"/pages/{page_id}", notion_version=NOTION_DATA_SOURCE_VERSION)
    except RuntimeError:
        page = notion_request("GET", f"/pages/{page_id}")
        
    parent = page.get("parent", {})
    db_id = parent.get("database_id") or parent.get("data_source_id")
    
    available_options = []
    if db_id:
        try:
            schema = get_source_schema(db_id)
            status_prop = schema.get("properties", {}).get("Trạng thái", {})
            prop_type = status_prop.get("type")
            if prop_type == "status":
                options = status_prop.get("status", {}).get("options", [])
                available_options = [opt.get("name") for opt in options if opt.get("name")]
            elif prop_type == "select":
                options = status_prop.get("select", {}).get("options", [])
                available_options = [opt.get("name") for opt in options if opt.get("name")]
        except Exception:
            pass

    target_status = None
    if status_name in available_options:
        target_status = status_name
    else:
        for name in (fallback_status_names or []):
            if name in available_options:
                target_status = name
                break
        if not target_status and available_options:
            target_status = available_options[0]

    if not target_status:
        target_status = status_name

    page_properties = page.get("properties", {})
    status_prop = page_properties.get("Trạng thái", {})
    status_type = status_prop.get("type")
    
    properties = {}
    if status_type == "status":
        properties["Trạng thái"] = {"status": {"name": target_status}}
    elif status_type == "select":
        properties["Trạng thái"] = {"select": {"name": target_status}}
        
    if note_content:
        if "Ghi chú" in page_properties:
            properties["Ghi chú"] = {"rich_text": [{"type": "text", "text": {"content": note_content}}]}
        elif "Ghi chú thiết lập" in page_properties:
            properties["Ghi chú thiết lập"] = {"rich_text": [{"type": "text", "text": {"content": note_content}}]}
            
    if not properties:
        return
    payload = {"properties": properties}
    try:
        notion_request("PATCH", f"/pages/{page_id}", payload, notion_version=NOTION_DATA_SOURCE_VERSION)
    except RuntimeError:
        notion_request("PATCH", f"/pages/{page_id}", payload)



def save_state(path, output_path, count):
    state = {
        "last_exported_at": datetime.now().isoformat(timespec="seconds"),
        "last_output": str(output_path),
        "last_count": count,
    }
    Path(path).write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def _compact_unique(values):
    seen = []
    for value in values:
        text = str(value or "").strip()
        if text and text not in seen:
            seen.append(text)
    return seen


def _parse_budget_value(value):
    if value in (None, ""):
        return 0
    text = re.sub(r"[^\d,.-]", "", str(value))
    if not text:
        return 0
    if "," in text and "." in text:
        last_comma = text.rfind(",")
        last_dot = text.rfind(".")
        if last_comma > last_dot:
            text = text.replace(".", "").replace(",", ".")
        else:
            text = text.replace(",", "")
    elif "," in text:
        parts = text.split(",")
        text = "".join(parts) if len(parts[-1]) == 3 else text.replace(",", ".")
    elif "." in text:
        parts = text.split(".")
        if len(parts) > 1 and len(parts[-1]) == 3:
            text = "".join(parts)
    try:
        return float(text)
    except ValueError:
        return 0


def build_supabase_export_payload(database_id, pages, rows, output, sample_csv):
    notion_values = [notion_page_to_values(page) for page in pages]
    campaigns = _compact_unique(
        row.get("Campaign Name") or values.get("Tên chiến dịch") or values.get("Campaign Name")
        for row, values in zip(rows, notion_values)
    )
    objectives = _compact_unique(
        row.get("Campaign Objective") or values.get("Mục tiêu chiến dịch")
        for row, values in zip(rows, notion_values)
    )
    adsets = _compact_unique(row.get("Ad Set Name") for row in rows)
    audiences = _compact_unique(
        row.get("Custom Audiences")
        or row.get("Saved Audience")
        or values.get("Mẫu đối tượng")
        or values.get("Đối tượng tuỳ chỉnh")
        for row, values in zip(rows, notion_values)
    )
    budget_total = sum(
        _parse_budget_value(row.get("Ad Set Lifetime Budget") or row.get("Ad Set Daily Budget"))
        for row in rows
    )
    output_path = Path(output)
    external_id = f"desktop:{output_path.stem}"
    exported_at = datetime.now().isoformat(timespec="seconds")

    source_payload = {
        "database_id": database_id,
        "sample_csv": str(sample_csv),
        "notion_page_ids": [page.get("id") for page in pages],
        "campaign_names": campaigns,
        "objectives": objectives,
        "adset_names": adsets,
        "audiences": audiences,
    }
    plan = {
        "external_id": external_id,
        "name": campaigns[0] if campaigns else output_path.stem,
        "status": "exported",
        "objective": objectives[0] if objectives else "",
        "ads_count": len(rows),
        "adsets_count": len(adsets),
        "audiences_count": len(audiences),
        "budget_total": budget_total or None,
        "source": "desktop",
        "source_payload": source_payload,
        "notion_url": pages[0].get("url", "") if pages else "",
        "latest_csv_url": str(output_path),
        "last_exported_at": exported_at,
    }
    export_record = {
        "external_id": f"{external_id}:export",
        "file_name": output_path.name,
        "file_url": str(output_path),
        "rows_count": len(rows),
        "exported_by": os.environ.get("USER") or os.environ.get("USERNAME") or "desktop",
        "source_payload": {
            "database_id": database_id,
            "output_path": str(output_path),
            "notion_page_ids": source_payload["notion_page_ids"],
        },
    }
    return plan, export_record


def sync_export_to_supabase(database_id, pages, rows, output, sample_csv):
    if not is_supabase_sync_configured():
        return False

    plan, export_record = build_supabase_export_payload(database_id, pages, rows, output, sample_csv)
    synced_plan = upsert_ads_plan(plan)
    if isinstance(synced_plan, list) and synced_plan:
        export_record["plan_id"] = synced_plan[0].get("id")
    insert_ads_export(export_record)
    insert_sync_log(
        {
            "source": "desktop",
            "entity_type": "ads_plan",
            "entity_external_id": plan["external_id"],
            "status": "success",
            "message": f"Synced export {export_record['file_name']}",
            "payload": {"ads_count": len(rows), "file_name": export_record["file_name"]},
        }
    )
    return True


def create_notion_template(parent_page_id):
    payload = {
        "parent": {"type": "page_id", "page_id": parent_page_id},
        "title": [{"type": "text", "text": {"content": "Facebook Ads Bulk Import"}}],
        "properties": NOTION_PROPERTIES,
    }
    result = notion_request("POST", "/databases", payload)
    print("Đã tạo database Notion:")
    print(result.get("url", ""))
    print("Database ID:", result.get("id", ""))
    return result


def export_command(args):
    load_env(args.env)
    database_id = args.database_id or os.environ.get("NOTION_DATA_SOURCE_ID") or os.environ.get("NOTION_DATABASE_ID")
    if not database_id:
        database_id = DEFAULT_DATA_SOURCE_ID

    sample_csv = args.sample_csv or os.environ.get("SAMPLE_CSV", DEFAULT_SAMPLE_CSV)
    template_row_index = args.template_row_index
    if template_row_index is None:
        template_row_index = int(os.environ.get("TEMPLATE_ROW_INDEX", "0"))

    headers, sample_rows = read_sample_rows(sample_csv)
    if not headers:
        raise RuntimeError("File mẫu không có header")
    if sample_rows:
        index = min(max(template_row_index, 0), len(sample_rows) - 1)
        template_row = dict(sample_rows[index])
    else:
        template_row = {}
    pages = query_ready_pages(
        database_id,
        include_exported=args.include_exported,
        ready_names=getattr(args, "ready_status_names", None),
    )
    if not pages:
        print("Không có bài Ready mới trong Notion.")
        return {"count": 0, "output": None}

    rows = build_facebook_rows(pages, headers, template_row, load_mapping(args.mapping), sample_rows)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    export_dir = Path(args.env).resolve().parent / "exports"
    output_path = args.output or export_dir / f"facebook_bulk_{timestamp}.csv"
    output = write_facebook_csv(output_path, headers, rows)

    if args.mark_exported:
        for page in pages:
            update_exported(page["id"], page.get("properties", {}))

    save_state(Path(args.env).resolve().parent / STATE_FILE, output, len(rows))
    supabase_synced = False
    try:
        supabase_synced = sync_export_to_supabase(database_id, pages, rows, output, sample_csv)
    except Exception as exc:
        print(f"Cảnh báo: export CSV xong nhưng sync Supabase lỗi: {exc}", file=sys.stderr)
        try:
            insert_sync_log(
                {
                    "source": "desktop",
                    "entity_type": "ads_plan",
                    "entity_external_id": f"desktop:{Path(output).stem}",
                    "status": "error",
                    "message": str(exc),
                    "payload": {"output": str(output), "rows_count": len(rows)},
                }
            )
        except Exception:
            pass
    message = f"Đã xuất {len(rows)} quảng cáo từ Notion."
    notified = telegram_send(message)
    sent_doc = telegram_send_document(output, caption=f"File CSV import Facebook ({len(rows)} bài)")
    print(message)
    if supabase_synced:
        print("Đã sync dashboard Supabase.")
    if notified:
        print("Đã gửi thông báo Telegram.")
    if sent_doc:
        print("Đã gửi file CSV qua Telegram.")
    return {"count": len(rows), "output": str(output), "supabase_synced": supabase_synced}


def main():
    parser = argparse.ArgumentParser(description="Export bài quảng cáo từ Notion ra file Facebook bulk import.")
    parser.add_argument("--env", default=".env", help="Đường dẫn file .env")
    subparsers = parser.add_subparsers(dest="command", required=True)

    create_parser = subparsers.add_parser("create-notion-template", help="Tạo database Notion mẫu")
    create_parser.add_argument("--parent-page-id", required=True, help="ID page Notion đã share cho integration")

    export_parser = subparsers.add_parser("export", help="Xuất CSV Facebook từ bài Ready trong Notion")
    export_parser.add_argument("--database-id", help="Notion data source ID hoặc database ID")
    export_parser.add_argument("--sample-csv")
    export_parser.add_argument("--output", help="File CSV đầu ra")
    export_parser.add_argument("--mapping", help="File JSON map property Notion sang cột Facebook")
    export_parser.add_argument("--template-row-index", type=int)
    export_parser.add_argument("--include-exported", action="store_true", help="Xuất cả bài đã đánh dấu Exported")
    export_parser.add_argument("--mark-exported", action="store_true", help="Đánh dấu Exported sau khi xuất")

    args = parser.parse_args()
    load_env(args.env)
    if args.command == "create-notion-template":
        create_notion_template(args.parent_page_id)
    elif args.command == "export":
        export_command(args)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"Lỗi: {exc}", file=sys.stderr)
        sys.exit(1)
