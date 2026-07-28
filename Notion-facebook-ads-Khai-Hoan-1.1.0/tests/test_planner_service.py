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

    def test_each_flow_can_target_a_different_link_subset(self):
        payload = self.base_payload()
        first_flow = payload["flows"][0]
        first_flow["link_urls"] = list(payload["links"])
        payload["flows"].append(
            {
                **first_flow,
                "link_urls": [payload["links"][0]],
            }
        )

        result = preview_plan(payload)

        self.assertEqual(result["summary"]["items_count"], 3)
        self.assertEqual(result["flows"][0]["links"], payload["links"])
        self.assertEqual(result["flows"][1]["links"], [payload["links"][0]])
        self.assertEqual(
            [item["link"] for item in result["items"]],
            [payload["links"][0], payload["links"][1], payload["links"][0]],
        )

    def test_rejects_flow_without_assigned_links(self):
        payload = self.base_payload()
        payload["flows"][0]["link_urls"] = []
        with self.assertRaisesRegex(PlannerValidationError, "chưa được gán bài viết"):
            preview_plan(payload)

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
        self.assertEqual(result["flows"][0]["notion_values"]["Ngân sách trọn đời"], 0)
        self.assertEqual(result["flows"][0]["notion_values"]["Loại ngân sách"], "Daily")

    def test_lifetime_budget_clears_daily_budget(self):
        payload = self.base_payload()
        payload["flows"][0].update(
            {
                "custom_budget_values": {"Ngân sách trọn đời": "2400"},
                "start_time": "2026-07-26T09:00",
                "end_time": "2026-07-29T09:00",
            }
        )
        result = preview_plan(payload)
        values = result["flows"][0]["notion_values"]
        self.assertEqual(values["Ngân sách/ngày"], 0)
        self.assertEqual(values["Ngân sách trọn đời"], "2400")
        self.assertEqual(values["Loại ngân sách"], "Lifetime")

    def test_normalizes_browser_schedule_to_gmt_plus_seven(self):
        payload = self.base_payload()
        payload["flows"][0].update(
            {
                "start_time": "2026-07-26T09:05",
                "end_time": "2026-07-27T10:15",
            }
        )
        flow = preview_plan(payload)["flows"][0]
        self.assertEqual(flow["start_time"], "2026-07-26T09:05+07:00")
        self.assertEqual(flow["end_time"], "2026-07-27T10:15+07:00")
        self.assertEqual(flow["notion_values"]["Start Time"], flow["start_time"])
        self.assertEqual(flow["notion_values"]["Stop Time"], flow["end_time"])

    def test_rejects_end_not_after_start(self):
        payload = self.base_payload()
        payload["flows"][0].update(
            {
                "start_time": "2026-07-26T09:05",
                "end_time": "2026-07-26T09:05",
            }
        )
        with self.assertRaisesRegex(PlannerValidationError, "phải sau"):
            preview_plan(payload)

    def test_rejects_lifetime_budget_without_end(self):
        payload = self.base_payload()
        payload["flows"][0].update(
            {
                "custom_budget_values": {"Ngân sách trọn đời": "2400"},
                "start_time": "2026-07-26T09:05",
            }
        )
        with self.assertRaisesRegex(PlannerValidationError, "trọn đời"):
            preview_plan(payload)

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
