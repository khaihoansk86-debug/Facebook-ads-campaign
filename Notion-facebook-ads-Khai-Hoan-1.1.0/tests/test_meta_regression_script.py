import json
import tempfile
import unittest
from pathlib import Path

from scripts.meta_regression_10_ads import build_payload, ledger_object_ids


class MetaRegressionScriptTests(unittest.TestCase):
    def test_builds_ten_existing_post_ads_in_two_compatible_groups(self):
        links = [f"https://www.facebook.com/example/posts/{index}" for index in range(5)]

        payload = build_payload(links)

        self.assertEqual(payload["links"], links)
        self.assertEqual(len(payload["flows"]), 2)
        self.assertEqual(
            [flow["campaign_code"] for flow in payload["flows"]],
            ["ENG_BASE", "ENG_BASE"],
        )
        self.assertEqual(
            [flow["adset_code"] for flow in payload["flows"]],
            ["ENG_POST_COLD", "ENG_POST_COLD"],
        )
        self.assertTrue(all(flow["creative_mode"] == "existing_post" for flow in payload["flows"]))

    def test_ledger_ids_can_target_one_operation_for_recovery(self):
        ledger = {
            "operations": {
                "first": {
                    "flows": {
                        "1": {
                            "campaign_id": "campaign-1",
                            "adset_id": "adset-1",
                            "ads": {"story": {"ad_id": "ad-1", "creative_id": "creative-1"}},
                        }
                    }
                },
                "second": {
                    "flows": {
                        "1": {
                            "campaign_id": "campaign-2",
                            "adset_id": "adset-2",
                            "ads": {"story": {"ad_id": "ad-2", "creative_id": "creative-2"}},
                        }
                    }
                },
            }
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "ledger.json"
            path.write_text(json.dumps(ledger), encoding="utf-8")

            ids = ledger_object_ids(path, "second")

        self.assertEqual(ids["campaigns"], ["campaign-2"])
        self.assertEqual(ids["adsets"], ["adset-2"])
        self.assertEqual(ids["ads"], ["ad-2"])
        self.assertEqual(ids["creatives"], ["creative-2"])


if __name__ == "__main__":
    unittest.main()
