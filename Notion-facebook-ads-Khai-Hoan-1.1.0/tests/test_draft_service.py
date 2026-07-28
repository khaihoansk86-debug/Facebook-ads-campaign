import tempfile
import unittest
from pathlib import Path

from ads_core.draft_service import create_drafts_safely


def sample_flow(adset_code="ENG_VIDEO_COLD"):
    return {
        "campaign_code": "ENG_BASE",
        "adset_code": adset_code,
        "audience_codes": ["AUD_BROAD_PHAN_THIET"],
        "dataset_code": "DATASET_NONE",
        "budget_code": "BUD_DAILY_800_PHP",
        "placement_code": "PLC_FB_MSG_MOBILE",
        "custom_budget_values": {},
    }


class DraftServiceTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.ledger = Path(self.temp_dir.name) / "ledger.json"

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_creates_every_link_and_flow_once(self):
        calls = []

        def create_func(_database, link, _campaign, adsets, **_kwargs):
            calls.append((link, adsets[0]))
            return [{"id": f"page-{len(calls)}"}]

        payload = {
            "links": ["https://facebook.com/a", "https://facebook.com/b"],
            "flows": [sample_flow(), sample_flow("ENG_POST_COLD")],
        }
        result = create_drafts_safely(payload, "database", create_func, self.ledger)
        self.assertEqual((result["created"], result["skipped"], result["failed"]), (4, 0, 0))
        self.assertEqual(len(calls), 4)

    def test_creates_only_links_assigned_to_each_flow(self):
        calls = []

        def create_func(_database, link, _campaign, adsets, **_kwargs):
            calls.append((link, adsets[0]))
            return [{"id": f"page-{len(calls)}"}]

        first = sample_flow()
        first["link_urls"] = ["https://facebook.com/a", "https://facebook.com/b"]
        second = sample_flow("ENG_POST_COLD")
        second["link_urls"] = ["https://facebook.com/a"]
        payload = {
            "links": ["https://facebook.com/a", "https://facebook.com/b"],
            "flows": [first, second],
        }

        result = create_drafts_safely(payload, "database", create_func, self.ledger)

        self.assertEqual(result["created"], 3)
        self.assertEqual(
            calls,
            [
                ("https://facebook.com/a", "ENG_VIDEO_COLD"),
                ("https://facebook.com/b", "ENG_VIDEO_COLD"),
                ("https://facebook.com/a", "ENG_POST_COLD"),
            ],
        )

    def test_returns_notion_urls_for_created_and_skipped_items(self):
        def create_func(*_args, **_kwargs):
            return [{"id": "page-1", "url": "https://notion.so/page-1"}]

        payload = {"links": ["https://facebook.com/a"], "flows": [sample_flow()]}
        first = create_drafts_safely(payload, "database", create_func, self.ledger)
        second = create_drafts_safely(payload, "database", create_func, self.ledger)
        self.assertEqual(first["results"][0]["page_urls"], ["https://notion.so/page-1"])
        self.assertEqual(second["results"][0]["page_urls"], ["https://notion.so/page-1"])

    def test_retry_skips_completed_items(self):
        calls = []

        def create_func(*_args, **_kwargs):
            calls.append(1)
            return [{"id": "page-1"}]

        payload = {"links": ["https://facebook.com/a"], "flows": [sample_flow()]}
        first = create_drafts_safely(payload, "database", create_func, self.ledger)
        second = create_drafts_safely(payload, "database", create_func, self.ledger)
        self.assertEqual((first["created"], second["skipped"]), (1, 1))
        self.assertEqual(len(calls), 1)

    def test_retry_only_recreates_previous_failure(self):
        attempts = {}

        def create_func(_database, link, *_args, **_kwargs):
            attempts[link] = attempts.get(link, 0) + 1
            if link.endswith("/b") and attempts[link] == 1:
                raise RuntimeError("Lỗi Notion giả lập")
            return [{"id": f"page-{link[-1]}"}]

        payload = {
            "links": ["https://facebook.com/a", "https://facebook.com/b"],
            "flows": [sample_flow()],
        }
        first = create_drafts_safely(payload, "database", create_func, self.ledger)
        second = create_drafts_safely(payload, "database", create_func, self.ledger)
        self.assertEqual((first["created"], first["failed"]), (1, 1))
        self.assertEqual((second["created"], second["skipped"], second["failed"]), (1, 1, 0))
        self.assertEqual(attempts["https://facebook.com/a"], 1)
        self.assertEqual(attempts["https://facebook.com/b"], 2)

    def test_forwards_normalized_budget_and_schedule(self):
        received = {}

        def create_func(*_args, **kwargs):
            received.update(kwargs)
            return [{"id": "page-1"}]

        flow = sample_flow()
        flow.update(
            {
                "custom_budget_values": {"Ngân sách/ngày": "1200"},
                "start_time": "2026-07-26T09:05",
                "end_time": "2026-07-27T10:15",
            }
        )
        create_drafts_safely(
            {"links": ["https://facebook.com/a"], "flows": [flow]},
            "database",
            create_func,
            self.ledger,
        )
        self.assertEqual(received["custom_budget_values"], {"Ngân sách/ngày": "1200"})
        self.assertEqual(
            received["schedule_values"],
            {
                "Start Time": "2026-07-26T09:05+07:00",
                "Stop Time": "2026-07-27T10:15+07:00",
            },
        )


if __name__ == "__main__":
    unittest.main()
