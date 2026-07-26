import unittest

import bulk_ads_tool as tool


class FacebookCsvMappingTests(unittest.TestCase):
    def test_selects_video_template_from_bundle_and_audience(self):
        expected = "T1 Video/ThruPlay | Khách lạnh Phan Thiết"
        sample_rows = [
            {"Ad Set Name": "Dòng khác"},
            {"Ad Set Name": expected, "Video ID": "v:1668252937777735"},
        ]
        values = {
            "Tên nhóm QC": "Tương tác | Trên quảng cáo | Lượt xem video",
            "Mẫu đối tượng": "Khách lạnh Phan Thiết",
        }
        selected, matched = tool.choose_template_row(values, sample_rows, sample_rows[0])
        self.assertTrue(matched)
        self.assertEqual(selected["Ad Set Name"], expected)

    def test_keeps_known_ids_when_permalink_matches_template(self):
        link = "https://www.facebook.com/reel/1668252937777735/"
        row = {
            "Permalink": link.rstrip("/"),
            "Story ID": "s:122182158812616632",
            "Video ID": "v:1668252937777735",
            "Link Object ID": "o:492651163923601",
            "Creative Type": "Video Page Post Ad",
        }
        tool.clean_stale_creative_fields(row, {"Link bài viết": link}, template_permalink=link)
        self.assertEqual(row["Story ID"], "s:122182158812616632")
        self.assertEqual(row["Video ID"], "v:1668252937777735")
        self.assertEqual(row["Link Object ID"], "o:492651163923601")

    def test_clears_story_id_from_different_template_post(self):
        row = {
            "Permalink": "https://www.facebook.com/reel/1668252937777735",
            "Story ID": "s:old",
            "Video ID": "v:old",
            "Link Object ID": "o:old",
            "Creative Type": "Video Page Post Ad",
        }
        tool.clean_stale_creative_fields(
            row,
            {"Link bài viết": "https://www.facebook.com/reel/1668252937777735"},
            template_permalink="https://www.facebook.com/reel/9999999999999999/",
        )
        self.assertEqual(row["Story ID"], "")
        self.assertEqual(row["Video ID"], "v:1668252937777735")

    def test_planner_fields_may_override_matched_template(self):
        self.assertIn("Tên nhóm QC", tool.PLANNER_TEMPLATE_OVERRIDE_FIELDS)
        self.assertIn("Ngân sách/ngày", tool.PLANNER_TEMPLATE_OVERRIDE_FIELDS)
        self.assertIn("Mục tiêu tối ưu", tool.PLANNER_TEMPLATE_OVERRIDE_FIELDS)
        self.assertIn("Vị trí Facebook", tool.PLANNER_TEMPLATE_OVERRIDE_FIELDS)


if __name__ == "__main__":
    unittest.main()
