import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


class WebUiContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = (ROOT / "web_ui" / "index.html").read_text(encoding="utf-8")
        cls.javascript = (ROOT / "web_ui" / "app.js").read_text(encoding="utf-8")
        cls.styles = (ROOT / "web_ui" / "styles.css").read_text(encoding="utf-8")

    def test_audience_is_visibly_required(self):
        self.assertIn("Nhóm người xem", self.html)
        self.assertIn("required-hint", self.html)
        self.assertIn("Hãy chọn một nhóm người xem", self.javascript)

    def test_static_assets_are_versioned_to_avoid_stale_layout(self):
        self.assertRegex(self.html, r'href="styles\.css\?v=[^"]+"')
        self.assertRegex(self.html, r'src="app\.js\?v=[^"]+"')

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
        self.assertIn('id="budgetCurrency"', self.html)
        self.assertNotIn("<b>PHP</b>", self.html)
        self.assertIn("/api/meta/status?verify=true", self.javascript)
        self.assertIn("meta.account?.currency", self.javascript)
        self.assertIn("Số tiền tùy chỉnh phải là một số lớn hơn 0", self.javascript)

    def test_presets_have_separate_management_areas(self):
        self.assertIn('data-app-view="audiences"', self.html)
        self.assertIn('data-app-view="placements"', self.html)
        self.assertIn('data-app-view="budgets"', self.html)
        self.assertIn('id="libraryView"', self.html)
        self.assertIn("loadPresetLibrary", self.javascript)
        self.assertNotIn('data-config-tab=', self.html)

    def test_audience_library_uses_meta_like_controls_and_suggestions(self):
        self.assertIn("Đối tượng tùy chỉnh", self.javascript)
        self.assertIn("Đối tượng tương tự", self.javascript)
        self.assertIn("/api/meta/audiences", self.javascript)
        self.assertIn("audience-kind-card", self.styles)
        self.assertIn("Kiểm soát đối tượng", self.javascript)
        self.assertIn("Gợi ý đối tượng", self.javascript)
        self.assertIn('data-preset-field="Loại trừ đối tượng"', self.javascript)
        self.assertIn('data-preset-field="Nhắm mục tiêu chi tiết"', self.javascript)
        self.assertIn("Không bắt buộc · có thể để trống", self.javascript)
        self.assertIn("segmented-control", self.styles)

    def test_placement_library_uses_selectable_meta_like_controls(self):
        self.assertIn("placementFieldsHtml", self.javascript)
        self.assertIn("Thiết bị", self.javascript)
        self.assertIn("Nền tảng", self.javascript)
        self.assertIn("Bảng feed", self.javascript)
        self.assertIn("Facebook Reels", self.javascript)
        self.assertIn("Kết quả tìm kiếm", self.javascript)
        self.assertIn('data-preset-field="Vị trí Instagram"', self.javascript)
        self.assertIn("placement-platform-card", self.styles)

    def test_article_preview_does_not_hide_after_three_flows(self):
        self.assertNotIn("flows.slice(0,3)", self.javascript)
        self.assertIn("Cách chạy ${flowIndex+1}", self.javascript)
        self.assertIn("áp dụng cho các bài đang được chọn", self.html)

    def test_invalid_links_block_readiness(self):
        self.assertIn("isFacebookLink", self.javascript)
        self.assertIn("link không hợp lệ", self.javascript)

    def test_creative_previews_are_loaded_safely_and_lazily(self):
        self.assertIn("/api/meta/creative-previews", self.javascript)
        self.assertIn('loading="lazy"', self.javascript)
        self.assertIn("vẫn có thể lập kế hoạch", self.javascript)
        self.assertIn("creative-preview", self.javascript)
        self.assertIn(".link-select-content{min-width:0;overflow:hidden}", self.styles)
        self.assertIn("align-items:start", self.styles)

    def test_page_posts_can_be_imported_by_date_range(self):
        self.assertIn('id="openPagePostsButton"', self.html)
        self.assertIn('id="pagePostsDialog"', self.html)
        self.assertIn('id="pagePostsSince"', self.html)
        self.assertIn('id="pagePostsUntil"', self.html)
        self.assertIn("/api/meta/page-posts?since=", self.javascript)
        self.assertIn("addSelectedPagePosts", self.javascript)
        self.assertIn(".page-posts-dialog", self.styles)
        self.assertIn(".page-post-card", self.styles)

    def test_notion_results_have_open_links(self):
        self.assertIn("Mở Notion", self.javascript)

    def test_export_review_ui_is_available(self):
        self.assertIn("CSV dự phòng", self.html)
        self.assertIn("loadCandidates", self.javascript)
        self.assertIn("exportSelected", self.javascript)

    def test_review_is_primary_publish_flow(self):
        self.assertIn("/api/reviews", self.javascript)
        self.assertIn("Gửi kế hoạch duyệt", self.html)
        self.assertIn("Duyệt kế hoạch", self.html)
        self.assertIn("publishReviewButton", self.html)
        self.assertIn("PAUSED", self.javascript)


if __name__ == "__main__":
    unittest.main()
