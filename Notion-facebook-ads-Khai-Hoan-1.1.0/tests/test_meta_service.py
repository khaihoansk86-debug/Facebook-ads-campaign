import tempfile
import unittest
from pathlib import Path

from ads_core.meta_service import (
    MetaConfig,
    MetaValidationError,
    create_paused_meta_drafts,
    get_meta_status,
    preview_meta_plan,
    resolve_existing_posts,
)


class FakeMetaClient:
    def __init__(self, fail_ad_once=False):
        self.get_calls = []
        self.post_calls = []
        self.next_id = 0
        self.copy_count = 0
        self.fail_ad_once = fail_ad_once

    def get(self, path, **params):
        self.get_calls.append((path, params))
        if path.startswith("act_"):
            return {
                "id": "act_1",
                "name": "Test account",
                "account_status": 1,
                "currency": "USD",
                "timezone_name": "America/Los_Angeles",
            }
        if path == "page-1_123456":
            return {
                "id": "page-1_123456",
                "permalink_url": "https://www.facebook.com/page/posts/123456",
            }
        if path.startswith("source-adset-"):
            return {
                "id": path,
                "name": "Source ad set",
                "account_id": "1",
                "effective_status": "ACTIVE",
                "billing_event": "IMPRESSIONS",
                "optimization_goal": "POST_ENGAGEMENT",
                "bid_strategy": "LOWEST_COST_WITHOUT_CAP",
                "targeting": {"age_min": 18, "age_max": 45},
                "destination_type": "ON_POST",
            }
        raise AssertionError(f"Unexpected GET {path}")

    def post(self, path, **params):
        self.post_calls.append((path, params))
        self.next_id += 1
        if path.endswith("/campaigns"):
            return {"id": "campaign-1"}
        if path.endswith("/adsets"):
            self.copy_count += 1
            return {"id": f"adset-{self.copy_count}"}
        if path.startswith("adset-"):
            return {"success": True}
        if path.endswith("/adcreatives"):
            return {"id": f"creative-{self.next_id}"}
        if path.endswith("/ads"):
            if self.fail_ad_once:
                self.fail_ad_once = False
                raise RuntimeError("temporary ad failure")
            return {"id": f"ad-{self.next_id}"}
        raise AssertionError(f"Unexpected POST {path}")


class FakePageTokenClient:
    def __init__(self, page_assigned=True):
        self.page_assigned = page_assigned
        self.page_token_used = False

    def get(self, path, **params):
        if path == "me/accounts":
            data = []
            if self.page_assigned:
                data.append(
                    {
                        "id": "page-1",
                        "name": "Test Page",
                        "tasks": ["ADVERTISE", "ANALYZE"],
                        "access_token": "page-secret-token",
                    }
                )
            return {"data": data}
        if path == "page-1/published_posts" and self.page_token_used:
            return {
                "data": [
                    {
                        "id": "page-1_999",
                        "permalink_url": "https://www.facebook.com/test-page/videos/example",
                    }
                ]
            }
        raise AssertionError(f"Unexpected GET {path}")

    def with_access_token(self, access_token):
        self.asserted_page_token = access_token
        self.page_token_used = access_token == "page-secret-token"
        return self


def config():
    return MetaConfig(
        access_token="secret-token",
        api_version="v25.0",
        ad_account_id="act_1",
        page_id="page-1",
        adset_template_map={"ENG_POST_COLD": "source-adset-1"},
        default_adset_template_id="",
        allow_default_template=False,
        test_mode=True,
    )


def payload():
    return {
        "links": ["https://www.facebook.com/page/posts/123456"],
        "flows": [
            {
                "campaign_code": "ENG_BASE",
                "adset_code": "ENG_POST_COLD",
                "audience_codes": ["AUD_BROAD_PHAN_THIET"],
                "dataset_code": "DATASET_NONE",
                "budget_code": "BUD_DAILY_800_PHP",
                "custom_budget_values": {"Ngân sách/ngày": "50"},
                "start_time": "2026-07-28T09:00:00+07:00",
                "end_time": None,
                "placement_code": "PLC_FB_MSG_MOBILE",
                "creative_mode": "existing_post",
            }
        ],
        "ad_name": "API test",
    }


class MetaServiceTests(unittest.TestCase):
    def test_status_is_safe_and_never_returns_token(self):
        status = get_meta_status(config(), FakeMetaClient(), verify=True)
        self.assertTrue(status["connected"])
        self.assertEqual(status["account"]["currency"], "USD")
        self.assertNotIn("access_token", status)
        self.assertNotIn("secret-token", str(status))

    def test_preview_is_read_only_and_converts_budget_to_minor_units(self):
        client = FakeMetaClient()
        result = preview_meta_plan(payload(), config(), client)
        self.assertEqual(result["write_mode"], "PAUSED_ONLY")
        self.assertEqual(result["summary"]["ads_count"], 1)
        self.assertEqual(result["links"][0]["object_story_id"], "page-1_123456")
        self.assertEqual(result["flows"][0]["budget_minor"], 5000)
        self.assertEqual(client.post_calls, [])

    def test_unresolved_link_uses_in_memory_page_access_token(self):
        client = FakePageTokenClient()
        link = "https://www.facebook.com/test-page/videos/example"

        resolved = resolve_existing_posts([link], config(), client)

        self.assertEqual(resolved[link], "page-1_999")
        self.assertTrue(client.page_token_used)

    def test_unassigned_page_is_rejected_before_reading_posts(self):
        client = FakePageTokenClient(page_assigned=False)
        with self.assertRaisesRegex(MetaValidationError, "chưa được gán quyền"):
            resolve_existing_posts(
                ["https://www.facebook.com/test-page/videos/example"],
                config(),
                client,
            )

    def test_missing_exact_template_mapping_is_rejected(self):
        bad_config = MetaConfig(
            access_token="token",
            api_version="v25.0",
            ad_account_id="act_1",
            page_id="page-1",
            adset_template_map={},
            default_adset_template_id="source-default",
            allow_default_template=False,
            test_mode=True,
        )
        with self.assertRaises(MetaValidationError):
            preview_meta_plan(payload(), bad_config, FakeMetaClient())

    def test_create_is_paused_and_idempotent(self):
        client = FakeMetaClient()
        with tempfile.TemporaryDirectory() as temp_dir:
            ledger_path = Path(temp_dir) / "meta-ledger.json"
            created = create_paused_meta_drafts(payload(), config(), client, ledger_path)
            get_count_after_create = len(client.get_calls)
            repeated = create_paused_meta_drafts(payload(), config(), client, ledger_path)

        self.assertEqual(created["status"], "created")
        self.assertEqual(created["created"], 1)
        self.assertEqual(repeated["status"], "skipped")
        self.assertEqual(repeated["skipped"], 1)
        self.assertEqual(len(client.get_calls), get_count_after_create)

        campaign_call = next(params for path, params in client.post_calls if path.endswith("/campaigns"))
        self.assertEqual(campaign_call["status"], "PAUSED")
        self.assertFalse(campaign_call["is_adset_budget_sharing_enabled"])
        adset_call = next(params for path, params in client.post_calls if path.endswith("/adsets"))
        self.assertEqual(adset_call["status"], "PAUSED")
        self.assertEqual(adset_call["daily_budget"], 5000)
        self.assertEqual(adset_call["start_time"], "2026-07-28T09:00+07:00")
        ad_call = next(params for path, params in client.post_calls if path.endswith("/ads"))
        self.assertEqual(ad_call["status"], "PAUSED")

    def test_retry_after_ad_failure_reuses_campaign_adset_and_creative(self):
        client = FakeMetaClient(fail_ad_once=True)
        with tempfile.TemporaryDirectory() as temp_dir:
            ledger_path = Path(temp_dir) / "meta-ledger.json"
            with self.assertRaises(RuntimeError):
                create_paused_meta_drafts(payload(), config(), client, ledger_path)
            result = create_paused_meta_drafts(payload(), config(), client, ledger_path)

        self.assertEqual(result["status"], "created")
        self.assertEqual(sum(path.endswith("/campaigns") for path, _ in client.post_calls), 1)
        self.assertEqual(sum(path.endswith("/adsets") for path, _ in client.post_calls), 1)
        self.assertEqual(sum(path.endswith("/adcreatives") for path, _ in client.post_calls), 1)
        self.assertEqual(sum(path.endswith("/ads") for path, _ in client.post_calls), 2)

    def test_multiple_formats_share_one_campaign(self):
        multi_payload = payload()
        second_flow = {
            **multi_payload["flows"][0],
            "adset_code": "ENG_VIDEO_COLD",
            "budget_code": "BUD_DAILY_800_PHP",
            "custom_budget_values": {"Ngân sách/ngày": "10"},
            "end_time": None,
        }
        multi_payload["flows"].append(second_flow)
        multi_config = MetaConfig(
            **{
                **config().__dict__,
                "adset_template_map": {
                    "ENG_POST_COLD": "source-adset-1",
                    "ENG_VIDEO_COLD": "source-adset-2",
                },
            }
        )
        client = FakeMetaClient()
        with tempfile.TemporaryDirectory() as temp_dir:
            result = create_paused_meta_drafts(
                multi_payload,
                multi_config,
                client,
                Path(temp_dir) / "meta-ledger.json",
            )

        self.assertEqual(result["created"], 2)
        self.assertEqual(sum(path.endswith("/campaigns") for path, _ in client.post_calls), 1)
        self.assertEqual(sum(path.endswith("/adsets") for path, _ in client.post_calls), 2)
        self.assertEqual(sum(path.endswith("/adcreatives") for path, _ in client.post_calls), 1)
        self.assertEqual(sum(path.endswith("/ads") for path, _ in client.post_calls), 2)


if __name__ == "__main__":
    unittest.main()
