#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
import hashlib
import hmac
import json
import os
import secrets
import sys
import time
import traceback
import webbrowser
from http.cookies import SimpleCookie
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

import bulk_ads_tool as tool
from ads_core.draft_service import create_drafts_safely
from ads_core.export_service import ExportValidationError, export_selected_pages, list_export_candidates
from ads_core.meta_service import (
    MetaApiError,
    MetaConfig,
    MetaValidationError,
    create_paused_meta_drafts,
    get_meta_status,
    preview_meta_plan,
)
from ads_core.planner_service import PlannerValidationError, preview_plan, public_catalog
from ads_core.preset_service import (
    PresetValidationError,
    create_preset,
    list_presets,
    update_preset,
)
from ads_core.review_service import (
    DEFAULT_REVIEW_STORE_PATH,
    ReviewValidationError,
    decide_review,
    get_review,
    list_reviews,
    publish_review,
    submit_review,
)


APP_DIR = Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent
RESOURCE_DIR = Path(getattr(sys, "_MEIPASS", APP_DIR))
WEB_UI_DIR = RESOURCE_DIR / "web_ui"
ENV_PATH = APP_DIR / ".env"
WEB_READY_STATUS_NAMES = ["Done"]
APPROVER_COOKIE = "kh_ads_approver"
APPROVER_SESSION_SECONDS = 8 * 60 * 60


class AuthorizationError(PermissionError):
    pass


def _review_store_path() -> Path:
    configured = os.environ.get("PLANNER_REVIEW_STORE")
    return Path(configured).resolve() if configured else DEFAULT_REVIEW_STORE_PATH


def _approver_key() -> str:
    return os.environ.get("PLANNER_APPROVER_KEY", "")


def _session_secret() -> bytes:
    secret = os.environ.get("PLANNER_SESSION_SECRET") or _approver_key()
    return secret.encode("utf-8")


def _b64encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def _b64decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def _create_session(reviewer: str) -> tuple[str, dict]:
    now = int(time.time())
    session = {
        "role": "approver",
        "reviewer": str(reviewer or "IT/Ads Operator").strip()[:100] or "IT/Ads Operator",
        "csrf": secrets.token_urlsafe(24),
        "iat": now,
        "exp": now + APPROVER_SESSION_SECONDS,
    }
    encoded = _b64encode(json.dumps(session, separators=(",", ":")).encode("utf-8"))
    signature = _b64encode(hmac.new(_session_secret(), encoded.encode("ascii"), hashlib.sha256).digest())
    return f"{encoded}.{signature}", session


def _parse_session(handler: SimpleHTTPRequestHandler) -> dict | None:
    if not _session_secret():
        return None
    cookie = SimpleCookie()
    try:
        cookie.load(handler.headers.get("Cookie", ""))
        token = cookie[APPROVER_COOKIE].value
        encoded, supplied_signature = token.split(".", 1)
        expected_signature = _b64encode(
            hmac.new(_session_secret(), encoded.encode("ascii"), hashlib.sha256).digest()
        )
        if not hmac.compare_digest(supplied_signature, expected_signature):
            return None
        session = json.loads(_b64decode(encoded).decode("utf-8"))
        if session.get("role") != "approver" or int(session.get("exp", 0)) <= int(time.time()):
            return None
        return session
    except (KeyError, ValueError, TypeError, json.JSONDecodeError):
        return None


def _require_approver(handler: SimpleHTTPRequestHandler) -> dict:
    if not _approver_key():
        raise AuthorizationError("Máy chủ chưa cấu hình khóa dành cho người duyệt.")
    session = _parse_session(handler)
    if not session:
        raise AuthorizationError("Cần đăng nhập với quyền IT/Ads Operator.")
    supplied_csrf = handler.headers.get("X-CSRF-Token", "")
    if not hmac.compare_digest(str(session.get("csrf") or ""), supplied_csrf):
        raise AuthorizationError("Phiên xác thực không hợp lệ. Hãy đăng nhập lại.")
    return session


def _read_json(handler: SimpleHTTPRequestHandler) -> dict:
    try:
        size = int(handler.headers.get("Content-Length", "0"))
    except ValueError as exc:
        raise PlannerValidationError("Dung lượng yêu cầu không hợp lệ.") from exc
    if size <= 0 or size > 2_000_000:
        raise PlannerValidationError("Yêu cầu trống hoặc vượt quá dung lượng cho phép.")
    try:
        data = json.loads(handler.rfile.read(size).decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise PlannerValidationError("Dữ liệu JSON không hợp lệ.") from exc
    if not isinstance(data, dict):
        raise PlannerValidationError("Nội dung yêu cầu phải là một đối tượng JSON.")
    return data


class ApiHandler(SimpleHTTPRequestHandler):
    server_version = "KhaiHoanLocalWeb/1.0"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(WEB_UI_DIR), **kwargs)

    def guess_type(self, path: str) -> str:
        content_type = super().guess_type(path)
        if content_type.startswith("text/") and "charset=" not in content_type:
            return f"{content_type}; charset=utf-8"
        return content_type

    def _json(self, status: int, data: dict, extra_headers: dict[str, str] | None = None) -> None:
        payload = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        for name, value in (extra_headers or {}).items():
            self.send_header(name, value)
        self.end_headers()
        self.wfile.write(payload)

    def _error(self, status: int, message: str) -> None:
        self._json(status, {"ok": False, "error": message})

    def end_headers(self) -> None:
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "no-referrer")
        super().end_headers()

    def do_GET(self) -> None:
        parsed_url = urlparse(self.path)
        path = parsed_url.path
        if path == "/api/health":
            self._json(200, {"ok": True, "mode": "local", "service": "Khai Hoan Ads"})
            return
        if path == "/api/planner/catalog":
            self._json(200, {"ok": True, "catalog": public_catalog()})
            return
        if path == "/api/auth/me":
            tool.load_env(ENV_PATH)
            session = _parse_session(self)
            self._json(
                200,
                {
                    "ok": True,
                    "configured": bool(_approver_key()),
                    "authenticated": bool(session),
                    "role": session.get("role") if session else "content",
                    "reviewer": session.get("reviewer") if session else None,
                    "csrf_token": session.get("csrf") if session else None,
                },
            )
            return
        if path == "/api/reviews":
            self._json(200, {"ok": True, "reviews": list_reviews(_review_store_path())})
            return
        if path.startswith("/api/reviews/"):
            review_id = unquote(path.removeprefix("/api/reviews/")).strip("/")
            try:
                self._json(200, {"ok": True, "review": get_review(review_id, _review_store_path())})
            except ReviewValidationError as exc:
                self._error(404, str(exc))
            return
        if path.startswith("/api/presets/"):
            kind = path.removeprefix("/api/presets/").strip("/")
            try:
                self._json(200, {"ok": True, "kind": kind, "presets": list_presets(kind)})
            except PresetValidationError as exc:
                self._error(404, str(exc))
            return
        if path == "/api/config/status":
            tool.load_env(ENV_PATH)
            meta_config = MetaConfig.from_env()
            self._json(
                200,
                {
                    "ok": True,
                    "configured": {
                        "notion": bool(os.environ.get("NOTION_TOKEN")),
                        "data_source": bool(
                            os.environ.get("NOTION_DATA_SOURCE_ID") or os.environ.get("NOTION_DATABASE_ID")
                        ),
                        "telegram": bool(
                            os.environ.get("TELEGRAM_BOT_TOKEN") and os.environ.get("TELEGRAM_CHAT_ID")
                        ),
                        "meta": bool(meta_config.access_token and meta_config.ad_account_id),
                    },
                },
            )
            return
        if path == "/api/meta/status":
            try:
                tool.load_env(ENV_PATH)
                config = MetaConfig.from_env()
                verify = parse_qs(parsed_url.query).get("verify", ["false"])[0].lower() in {"1", "true", "yes"}
                self._json(200, {"ok": True, **get_meta_status(config, verify=verify)})
            except MetaValidationError as exc:
                self._error(400, str(exc))
            except MetaApiError as exc:
                self._error(502, str(exc))
            return
        if path == "/api/export/candidates":
            try:
                tool.load_env(ENV_PATH)
                database_id = (
                    os.environ.get("NOTION_DATA_SOURCE_ID")
                    or os.environ.get("NOTION_DATABASE_ID")
                    or tool.DEFAULT_DATA_SOURCE_ID
                )
                candidates = list_export_candidates(
                    database_id,
                    tool.query_ready_pages,
                    tool.notion_page_to_values,
                    ready_names=WEB_READY_STATUS_NAMES,
                )
                self._json(200, {"ok": True, "candidates": candidates})
            except Exception as exc:
                traceback.print_exc()
                self._error(500, f"Không thể đọc danh sách Notion: {exc}")
            return
        if path.startswith("/api/exports/"):
            file_name = Path(unquote(path.removeprefix("/api/exports/"))).name
            export_dir = (APP_DIR / "exports").resolve()
            file_path = (export_dir / file_name).resolve()
            if file_path.parent != export_dir or not file_path.is_file() or file_path.suffix.lower() != ".csv":
                self._error(404, "Không tìm thấy file CSV.")
                return
            payload = file_path.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/csv; charset=utf-16")
            self.send_header("Content-Disposition", f'attachment; filename="{file_path.name}"')
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
            return
        super().do_GET()

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        try:
            if path == "/api/auth/approver":
                tool.load_env(ENV_PATH)
                configured_key = _approver_key()
                if not configured_key:
                    self._error(503, "Máy chủ chưa cấu hình PLANNER_APPROVER_KEY.")
                    return
                credentials = _read_json(self)
                supplied_key = str(credentials.get("key") or "")
                if not hmac.compare_digest(configured_key, supplied_key):
                    self._error(401, "Khóa người duyệt không đúng.")
                    return
                token, session = _create_session(credentials.get("reviewer") or "IT/Ads Operator")
                secure = self.headers.get("X-Forwarded-Proto", "").lower() == "https"
                cookie = (
                    f"{APPROVER_COOKIE}={token}; Path=/; HttpOnly; SameSite=Strict; "
                    f"Max-Age={APPROVER_SESSION_SECONDS}"
                )
                if secure:
                    cookie += "; Secure"
                self._json(
                    200,
                    {
                        "ok": True,
                        "authenticated": True,
                        "role": session["role"],
                        "reviewer": session["reviewer"],
                        "csrf_token": session["csrf"],
                    },
                    {"Set-Cookie": cookie},
                )
                return
            if path == "/api/reviews":
                review, deduplicated = submit_review(_read_json(self), _review_store_path())
                self._json(
                    200 if deduplicated else 201,
                    {"ok": True, "review": review, "deduplicated": deduplicated},
                )
                return
            review_parts = path.strip("/").split("/")
            if len(review_parts) == 4 and review_parts[:2] == ["api", "reviews"]:
                _, _, review_id, action = review_parts
                session = _require_approver(self)
                action_payload = _read_json(self)
                if action in {"approve", "reject"}:
                    decision = "APPROVED" if action == "approve" else "REJECTED"
                    review = decide_review(
                        unquote(review_id),
                        decision,
                        session["reviewer"],
                        action_payload.get("note") or "",
                        _review_store_path(),
                    )
                    self._json(200, {"ok": True, "review": review})
                    return
                if action == "publish":
                    tool.load_env(ENV_PATH)
                    config = MetaConfig.from_env()
                    review = publish_review(
                        unquote(review_id),
                        lambda review_payload: create_paused_meta_drafts(review_payload, config),
                        _review_store_path(),
                    )
                    self._json(200, {"ok": True, "review": review})
                    return
            if path.startswith("/api/presets/"):
                kind = path.removeprefix("/api/presets/").strip("/")
                preset = create_preset(kind, _read_json(self))
                self._json(201, {"ok": True, "preset": preset})
                return
            if path == "/api/planner/preview":
                result = preview_plan(_read_json(self))
                self._json(200, {"ok": True, "plan": result})
                return
            if path == "/api/meta/preview":
                payload = _read_json(self)
                tool.load_env(ENV_PATH)
                config = MetaConfig.from_env()
                result = preview_meta_plan(payload, config)
                self._json(200, {"ok": True, "plan": result})
                return
            if path == "/api/meta/drafts":
                _require_approver(self)
                payload = _read_json(self)
                tool.load_env(ENV_PATH)
                config = MetaConfig.from_env()
                result = create_paused_meta_drafts(payload, config)
                self._json(200, {"ok": True, **result})
                return
            if path == "/api/planner/drafts":
                payload = _read_json(self)
                tool.load_env(ENV_PATH)
                data_source_id = (
                    os.environ.get("NOTION_DATA_SOURCE_ID")
                    or os.environ.get("NOTION_DATABASE_ID")
                    or tool.DEFAULT_DATA_SOURCE_ID
                )
                result = create_drafts_safely(
                    payload,
                    data_source_id,
                    tool.create_notion_ad_drafts_from_bundles,
                )
                self._json(200, {"ok": True, **result})
                return
            if path == "/api/export":
                payload = _read_json(self)
                tool.load_env(ENV_PATH)
                database_id = (
                    os.environ.get("NOTION_DATA_SOURCE_ID")
                    or os.environ.get("NOTION_DATABASE_ID")
                    or tool.DEFAULT_DATA_SOURCE_ID
                )
                sample_csv = Path(
                    os.environ.get("SAMPLE_CSV")
                    or RESOURCE_DIR / "sample" / "facebook_ads_template.csv"
                )
                if not sample_csv.is_absolute():
                    sample_csv = (APP_DIR / sample_csv).resolve()
                if not sample_csv.exists():
                    bundled_sample = RESOURCE_DIR / "sample" / "facebook_ads_template.csv"
                    if bundled_sample.exists():
                        sample_csv = bundled_sample
                result = export_selected_pages(
                    database_id=database_id,
                    selected_page_ids=payload.get("page_ids") or [],
                    sample_csv=sample_csv,
                    template_row_index=int(os.environ.get("TEMPLATE_ROW_INDEX", "0")),
                    output_dir=APP_DIR / "exports",
                    mapping=tool.load_mapping(None),
                    query_func=tool.query_ready_pages,
                    build_rows_func=tool.build_facebook_rows,
                    mark_exported_func=tool.update_exported,
                    ready_names=WEB_READY_STATUS_NAMES,
                    sync_func=tool.sync_export_to_supabase,
                )
                result["download_url"] = f"/api/exports/{result['file_name']}"
                self._json(200, {"ok": True, **result})
                return
            self._error(404, "Không tìm thấy API.")
        except PlannerValidationError as exc:
            self._error(400, str(exc))
        except ExportValidationError as exc:
            self._error(400, str(exc))
        except PresetValidationError as exc:
            self._error(400, str(exc))
        except MetaValidationError as exc:
            self._error(400, str(exc))
        except MetaApiError as exc:
            self._error(502, str(exc))
        except ReviewValidationError as exc:
            self._error(409, str(exc))
        except AuthorizationError as exc:
            self._error(403, str(exc))
        except Exception as exc:
            traceback.print_exc()
            self._error(500, f"Không thể hoàn tất yêu cầu: {exc}")

    def do_DELETE(self) -> None:
        path = urlparse(self.path).path
        if path == "/api/auth/session":
            self._json(
                200,
                {"ok": True, "authenticated": False},
                {
                    "Set-Cookie": (
                        f"{APPROVER_COOKIE}=; Path=/; HttpOnly; SameSite=Strict; "
                        "Max-Age=0"
                    )
                },
            )
            return
        self._error(404, "Không tìm thấy API.")

    def do_PUT(self) -> None:
        path = urlparse(self.path).path
        try:
            parts = path.strip("/").split("/")
            if len(parts) == 4 and parts[:2] == ["api", "presets"]:
                _, _, kind, code = parts
                preset = update_preset(kind, unquote(code), _read_json(self))
                self._json(200, {"ok": True, "preset": preset})
                return
            self._error(404, "Không tìm thấy API.")
        except (PlannerValidationError, PresetValidationError) as exc:
            self._error(400, str(exc))
        except Exception as exc:
            traceback.print_exc()
            self._error(500, f"Không thể hoàn tất yêu cầu: {exc}")

    def log_message(self, fmt: str, *args) -> None:
        print(f"{self.address_string()} - {fmt % args}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Chạy Khải Hoàn Ads trên trình duyệt của máy hiện tại.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args()
    server = ThreadingHTTPServer((args.host, args.port), ApiHandler)
    url = f"http://{args.host}:{args.port}"
    print(f"Khải Hoàn Ads đang chạy tại {url}")
    print("Nhấn Ctrl+C để dừng.")
    if not args.no_browser:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nĐã dừng máy chủ.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
