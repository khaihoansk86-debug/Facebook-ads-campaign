import json
import threading
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from unittest.mock import patch

import web_app


class WebApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), web_app.ApiHandler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.base_url = f"http://127.0.0.1:{cls.server.server_port}"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=2)

    def request(self, path, payload=None, method=None):
        data = None if payload is None else json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            self.base_url + path,
            data=data,
            method=method or ("GET" if payload is None else "POST"),
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(request, timeout=3) as response:
                return response.status, json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            try:
                return exc.code, json.loads(exc.read().decode("utf-8"))
            finally:
                exc.close()

    def payload(self):
        return {
            "links": ["https://facebook.com/a", "https://facebook.com/b"],
            "flows": [
                {
                    "campaign_code": "ENG_BASE",
                    "adset_code": "ENG_VIDEO_COLD",
                    "audience_codes": ["AUD_BROAD_PHAN_THIET"],
                    "dataset_code": "DATASET_NONE",
                    "budget_code": "BUD_DAILY_800_PHP",
                    "placement_code": "PLC_FB_MSG_MOBILE",
                }
            ],
        }

    def test_health_and_catalog(self):
        status, health = self.request("/api/health")
        _, catalog = self.request("/api/planner/catalog")
        self.assertEqual(status, 200)
        self.assertTrue(health["ok"])
        self.assertEqual(len(catalog["catalog"]["campaigns"]), 5)
        self.assertEqual(len(catalog["catalog"]["adsets"]), 70)

    def test_static_html_declares_utf8(self):
        with urllib.request.urlopen(self.base_url + "/", timeout=3) as response:
            content_type = response.headers.get("Content-Type", "")
            html = response.read().decode("utf-8")
        self.assertIn("charset=utf-8", content_type.lower())
        self.assertIn("CSV dự phòng", html)

    def test_preview_and_validation_error(self):
        status, result = self.request("/api/planner/preview", self.payload())
        self.assertEqual(status, 200)
        self.assertEqual(result["plan"]["summary"]["items_count"], 2)
        invalid = self.payload()
        invalid["links"] = []
        status, result = self.request("/api/planner/preview", invalid)
        self.assertEqual(status, 400)
        self.assertFalse(result["ok"])

    def test_drafts_endpoint_returns_detailed_counts(self):
        fake_result = {"total": 2, "created": 1, "skipped": 1, "failed": 0, "results": []}
        with patch("web_app.create_drafts_safely", return_value=fake_result):
            status, result = self.request("/api/planner/drafts", self.payload())
        self.assertEqual(status, 200)
        self.assertEqual(result["created"], 1)
        self.assertEqual(result["skipped"], 1)

    def test_config_status_does_not_expose_tokens(self):
        status, result = self.request("/api/config/status")
        self.assertEqual(status, 200)
        self.assertNotIn("NOTION_TOKEN", result)
        self.assertNotIn("SUPABASE_SECRET_KEY", result)

    def test_meta_status_does_not_expose_token(self):
        safe_status = {
            "configured": True,
            "api_version": "v25.0",
            "account_id": "act_1",
            "template_codes": ["ENG_POST_COLD"],
        }
        with patch("web_app.get_meta_status", return_value=safe_status):
            status, result = self.request("/api/meta/status")
        self.assertEqual(status, 200)
        self.assertTrue(result["configured"])
        self.assertNotIn("META_ACCESS_TOKEN", result)

    def test_meta_preview_and_paused_create_endpoints(self):
        fake_preview = {
            "summary": {"campaigns_count": 1, "adsets_count": 1, "ads_count": 2},
            "write_mode": "PAUSED_ONLY",
        }
        with patch("web_app.preview_meta_plan", return_value=fake_preview):
            status, result = self.request("/api/meta/preview", self.payload())
        self.assertEqual(status, 200)
        self.assertEqual(result["plan"]["write_mode"], "PAUSED_ONLY")

        fake_created = {"status": "created", "created": 2, "skipped": 0, "failed": 0}
        with patch("web_app.create_paused_meta_drafts", return_value=fake_created):
            status, result = self.request("/api/meta/drafts", self.payload())
        self.assertEqual(status, 200)
        self.assertEqual(result["created"], 2)

    def test_export_candidates_endpoint(self):
        candidates = [{"id": "page-1", "name": "Bài đã duyệt", "status": "Ready"}]
        with patch("web_app.list_export_candidates", return_value=candidates):
            status, result = self.request("/api/export/candidates")
        self.assertEqual(status, 200)
        self.assertEqual(result["candidates"], candidates)
        called_ready_names = web_app.WEB_READY_STATUS_NAMES
        self.assertEqual(called_ready_names, ["Done"])

    def test_export_endpoint_returns_download_url(self):
        fake_result = {
            "count": 1,
            "file_name": "facebook_web_test.csv",
            "output": "exports/facebook_web_test.csv",
            "page_ids": ["page-1"],
            "sync_warning": "",
        }
        with patch("web_app.export_selected_pages", return_value=fake_result):
            status, result = self.request("/api/export", {"page_ids": ["page-1"]})
        self.assertEqual(status, 200)
        self.assertEqual(result["download_url"], "/api/exports/facebook_web_test.csv")

    def test_preset_endpoints(self):
        preset = {"code": "AUD_TEST", "name": "Tệp thử", "summary": "", "notionValues": {"Tuổi min": 18}}
        with patch("web_app.list_presets", return_value=[preset]):
            status, result = self.request("/api/presets/audiences")
        self.assertEqual(status, 200)
        self.assertEqual(result["presets"][0]["code"], "AUD_TEST")

        with patch("web_app.create_preset", return_value=preset):
            status, result = self.request("/api/presets/audiences", preset)
        self.assertEqual(status, 201)
        self.assertEqual(result["preset"]["name"], "Tệp thử")

        updated = {**preset, "name": "Tệp đã sửa"}
        with patch("web_app.update_preset", return_value=updated):
            status, result = self.request("/api/presets/audiences/AUD_TEST", updated, method="PUT")
        self.assertEqual(status, 200)
        self.assertEqual(result["preset"]["name"], "Tệp đã sửa")


if __name__ == "__main__":
    unittest.main()
