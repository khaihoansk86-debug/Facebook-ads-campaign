import tempfile
import unittest
from pathlib import Path

from ads_core.review_service import (
    ReviewValidationError,
    decide_review,
    get_review,
    list_reviews,
    publish_review,
    submit_review,
)


class ReviewServiceTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.store_path = Path(self.temp_dir.name) / "reviews.json"
        self.payload = {
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
            "submitted_by": "Content A",
        }

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_submit_builds_meta_style_tree_and_deduplicates(self):
        review, duplicate = submit_review(self.payload, self.store_path)
        second, second_duplicate = submit_review(self.payload, self.store_path)

        self.assertFalse(duplicate)
        self.assertTrue(second_duplicate)
        self.assertEqual(second["id"], review["id"])
        self.assertEqual(review["status"], "PENDING_REVIEW")
        self.assertEqual(review["summary"]["campaigns_count"], 1)
        self.assertEqual(review["summary"]["adsets_count"], 1)
        self.assertEqual(review["summary"]["ads_count"], 2)
        self.assertEqual(len(review["tree"][0]["adsets"][0]["ads"]), 2)
        self.assertNotIn("payload", list_reviews(self.store_path)[0])

    def test_approval_is_required_before_publish(self):
        review, _ = submit_review(self.payload, self.store_path)
        with self.assertRaises(ReviewValidationError):
            publish_review(review["id"], lambda _payload: {"created": 2}, self.store_path)

        approved = decide_review(review["id"], "APPROVED", "IT A", "Đã kiểm tra", self.store_path)
        published = publish_review(
            review["id"],
            lambda payload: {"created": len(payload["links"]), "status": "created"},
            self.store_path,
        )

        self.assertEqual(approved["status"], "APPROVED")
        self.assertEqual(published["status"], "META_CREATED")
        self.assertEqual(published["meta_result"]["created"], 2)
        self.assertEqual(get_review(review["id"], self.store_path)["status"], "META_CREATED")

    def test_rejection_requires_reason(self):
        review, _ = submit_review(self.payload, self.store_path)
        with self.assertRaises(ReviewValidationError):
            decide_review(review["id"], "REJECTED", "IT A", "", self.store_path)


if __name__ == "__main__":
    unittest.main()
