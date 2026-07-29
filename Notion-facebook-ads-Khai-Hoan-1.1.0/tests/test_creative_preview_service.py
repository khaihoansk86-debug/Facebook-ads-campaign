import tempfile
import unittest
from pathlib import Path

from ads_core.creative_preview_service import get_creative_previews
from ads_core.meta_service import MetaApiError, MetaConfig, MetaValidationError


class FakeCreativeClient:
    def __init__(self, *, include_post=True):
        self.get_calls = []
        self.include_post = include_post

    def get(self, path, **params):
        self.get_calls.append((path, params))
        if path == "me/accounts":
            return {
                "data": [
                    {
                        "id": "111",
                        "name": "Khải Hoàn",
                        "tasks": ["ADVERTISE", "ANALYZE"],
                        "access_token": "page-secret-token",
                    }
                ]
            }
        if path == "":
            if not self.include_post:
                return {}
            return {
                "111_123": {
                    "id": "111_123",
                    "message": "Nội dung creative dùng để kiểm tra.",
                    "permalink_url": "https://www.facebook.com/page/posts/123",
                    "created_time": "2026-07-28T09:00:00+0000",
                    "from": {"id": "111", "name": "Khải Hoàn"},
                    "attachments": {
                        "data": [
                            {
                                "media_type": "photo",
                                "media": {
                                    "image": {
                                        "src": "https://scontent.example.com/creative.jpg"
                                    }
                                },
                            }
                        ]
                    },
                }
            }
        raise AssertionError(f"Unexpected GET {path}")

    def with_access_token(self, access_token):
        self.page_token_used = access_token == "page-secret-token"
        return self


class FakeMixedBatchClient(FakeCreativeClient):
    def get(self, path, **params):
        if path == "":
            self.get_calls.append((path, params))
            ids = str(params.get("ids") or "").split(",")
            if len(ids) > 1:
                raise MetaApiError("One object in the batch is invalid.")
            if ids == ["111_123"]:
                return FakeCreativeClient.get(self, path, **params)
            return {}
        return FakeCreativeClient.get(self, path, **params)


def config():
    return MetaConfig(
        access_token="secret-token",
        api_version="v25.0",
        ad_account_id="act_1",
        page_id="111",
        adset_template_map={},
        default_adset_template_id="",
        allow_default_template=False,
        test_mode=True,
    )


class CreativePreviewServiceTests(unittest.TestCase):
    def test_reads_creative_metadata_in_one_graph_batch_and_caches_it(self):
        link = "https://www.facebook.com/page/posts/123"
        with tempfile.TemporaryDirectory() as temp_dir:
            cache_path = Path(temp_dir) / "previews.json"
            first_client = FakeCreativeClient()
            first = get_creative_previews(
                [link],
                config(),
                first_client,
                cache_path=cache_path,
                now=1000,
            )
            second_client = FakeCreativeClient()
            second = get_creative_previews(
                [link],
                config(),
                second_client,
                cache_path=cache_path,
                now=1001,
            )
            cached_text = cache_path.read_text(encoding="utf-8")

        preview = first["previews"][0]
        self.assertEqual(first["summary"]["ready"], 1)
        self.assertEqual(preview["page_name"], "Khải Hoàn")
        self.assertEqual(preview["media_type"], "photo")
        self.assertEqual(preview["object_story_id"], "111_123")
        self.assertIn("Nội dung creative", preview["message"])
        self.assertEqual(len(first_client.get_calls), 2)
        self.assertTrue(first_client.page_token_used)
        self.assertEqual(second["previews"][0], preview)
        self.assertEqual(second_client.get_calls, [])
        self.assertNotIn("secret-token", cached_text)

    def test_unreadable_graph_object_returns_soft_failure(self):
        link = "https://www.facebook.com/page/posts/123"
        with tempfile.TemporaryDirectory() as temp_dir:
            result = get_creative_previews(
                [link],
                config(),
                FakeCreativeClient(include_post=False),
                cache_path=Path(temp_dir) / "previews.json",
            )

        self.assertEqual(result["summary"]["unavailable"], 1)
        self.assertEqual(result["previews"][0]["status"], "unavailable")
        self.assertEqual(result["previews"][0]["permalink_url"], link)

    def test_one_bad_object_does_not_hide_other_creatives_in_batch(self):
        photo = "https://www.facebook.com/page/posts/123"
        bad = "https://www.facebook.com/999_888"
        with tempfile.TemporaryDirectory() as temp_dir:
            result = get_creative_previews(
                [photo, bad],
                config(),
                FakeMixedBatchClient(),
                cache_path=Path(temp_dir) / "previews.json",
            )

        self.assertEqual(
            [preview["status"] for preview in result["previews"]],
            ["ready", "unavailable"],
        )
        self.assertEqual(result["summary"], {"total": 2, "ready": 1, "unavailable": 1})

    def test_rejects_non_facebook_links_and_oversized_batches(self):
        with self.assertRaisesRegex(MetaValidationError, "không hợp lệ"):
            get_creative_previews(["https://example.com/post"], config())
        with self.assertRaisesRegex(MetaValidationError, "tối đa 100"):
            get_creative_previews(
                [f"https://facebook.com/page/posts/{index}" for index in range(101)],
                config(),
            )


if __name__ == "__main__":
    unittest.main()
