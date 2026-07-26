import unittest

from ads_core.planner_service import PlannerValidationError, preview_plan


class PlannerServiceTests(unittest.TestCase):
    def base_payload(self):
        return {
            "links": ["https://facebook.com/post-a", "https://facebook.com/post-b"],
            "flows": [
                {
                    "campaign_code": "ENG_BASE",
                    "adset_code": "ENG_VIDEO_COLD",
                    "audience_codes": ["AUD_BROAD_PHAN_THIET"],
                    "dataset_code": "DATASET_NONE",
                    "budget_code": "BUD_DAILY_800_PHP",
                    "placement_code": "PLC_FB_MSG_MOBILE",
                    "custom_budget_values": {},
                }
            ],
        }

    def test_two_links_one_flow_create_two_items(self):
        result = preview_plan(self.base_payload())
        self.assertEqual(result["summary"], {"links_count": 2, "flows_count": 1, "items_count": 2})

    def test_rejects_adset_from_another_campaign(self):
        payload = self.base_payload()
        payload["flows"][0]["adset_code"] = "TRAFFIC_WEBSITE_LPV"
        with self.assertRaises(PlannerValidationError):
            preview_plan(payload)

    def test_custom_budget_overrides_preset(self):
        payload = self.base_payload()
        payload["flows"][0]["custom_budget_values"] = {"Ngân sách/ngày": 1200}
        result = preview_plan(payload)
        self.assertEqual(result["flows"][0]["notion_values"]["Ngân sách/ngày"], 1200)

    def test_rejects_invalid_custom_budget(self):
        for invalid in (0, -100, "abc"):
            with self.subTest(invalid=invalid):
                payload = self.base_payload()
                payload["flows"][0]["custom_budget_values"] = {"Ngân sách/ngày": invalid}
                with self.assertRaisesRegex(PlannerValidationError, "lớn hơn 0"):
                    preview_plan(payload)

    def test_rejects_missing_links(self):
        payload = self.base_payload()
        payload["links"] = []
        with self.assertRaises(PlannerValidationError):
            preview_plan(payload)

    def test_rejects_non_facebook_link(self):
        payload = self.base_payload()
        payload["links"] = ["https://example.com/not-facebook"]
        with self.assertRaisesRegex(PlannerValidationError, "Không phải đường dẫn Facebook"):
            preview_plan(payload)

    def test_rejects_missing_required_dataset(self):
        payload = self.base_payload()
        payload["flows"][0].update(
            {
                "campaign_code": "SALES_BASE",
                "adset_code": "SALE_WEB_APP",
                "dataset_code": "DATASET_NONE",
            }
        )
        with self.assertRaisesRegex(PlannerValidationError, "yêu cầu chọn nguồn dữ liệu"):
            preview_plan(payload)

    def test_rejects_missing_audience(self):
        payload = self.base_payload()
        payload["flows"][0]["audience_codes"] = []
        with self.assertRaisesRegex(PlannerValidationError, "đúng một nhóm người xem"):
            preview_plan(payload)

    def test_new_drafts_are_not_immediately_exportable(self):
        from bulk_ads_tool import DEFAULT_READY_STATUS_NAMES, DRAFT_DEFAULT_VALUES

        self.assertEqual(DRAFT_DEFAULT_VALUES["Trạng thái"], "In progress")
        self.assertNotIn("In progress", DEFAULT_READY_STATUS_NAMES)
        self.assertNotIn("Not started", DEFAULT_READY_STATUS_NAMES)


if __name__ == "__main__":
    unittest.main()
