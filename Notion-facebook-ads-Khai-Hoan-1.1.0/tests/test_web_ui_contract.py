import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


class WebUiContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = (ROOT / "web_ui" / "index.html").read_text(encoding="utf-8")
        cls.javascript = (ROOT / "web_ui" / "app.js").read_text(encoding="utf-8")

    def test_audience_is_visibly_required(self):
        self.assertIn("Nhóm người xem", self.html)
        self.assertIn("required-hint", self.html)
        self.assertIn("Hãy chọn một nhóm người xem", self.javascript)

    def test_flows_can_be_edited(self):
        self.assertIn("data-edit", self.javascript)
        self.assertIn("Lưu thay đổi cách chạy", self.javascript)
        self.assertIn("Hủy chỉnh sửa", self.javascript)
        self.assertIn("cách chạy cũ được giữ nguyên", self.javascript)

    def test_flow_cards_show_operational_details(self):
        self.assertIn("flow-meta", self.javascript)
        self.assertIn("audience.name", self.javascript)
        self.assertIn("placement.name", self.javascript)

    def test_custom_budget_has_guidance_and_validation(self):
        self.assertIn("sẽ thay ngân sách mẫu", self.html)
        self.assertIn("Số tiền tùy chỉnh phải là một số lớn hơn 0", self.javascript)

    def test_presets_have_separate_management_areas(self):
        self.assertIn('data-app-view="audiences"', self.html)
        self.assertIn('data-app-view="placements"', self.html)
        self.assertIn('data-app-view="budgets"', self.html)
        self.assertIn('id="libraryView"', self.html)
        self.assertIn("loadPresetLibrary", self.javascript)
        self.assertNotIn('data-config-tab=', self.html)

    def test_article_preview_does_not_hide_after_three_flows(self):
        self.assertNotIn("flows.slice(0,3)", self.javascript)
        self.assertIn("Cách chạy ${flowIndex+1}", self.javascript)
        self.assertIn("áp dụng cho tất cả bài viết", self.html)

    def test_invalid_links_block_readiness(self):
        self.assertIn("isFacebookLink", self.javascript)
        self.assertIn("link không hợp lệ", self.javascript)

    def test_notion_results_have_open_links(self):
        self.assertIn("Mở trang Notion", self.javascript)

    def test_export_review_ui_is_available(self):
        self.assertIn("Duyệt & xuất CSV", self.html)
        self.assertIn("loadCandidates", self.javascript)
        self.assertIn("exportSelected", self.javascript)


if __name__ == "__main__":
    unittest.main()
