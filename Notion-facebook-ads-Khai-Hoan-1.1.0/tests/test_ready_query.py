import unittest
from unittest.mock import patch

import bulk_ads_tool


class ReadyQueryTests(unittest.TestCase):
    @patch("bulk_ads_tool.notion_request")
    @patch("bulk_ads_tool.get_source_schema")
    def test_returns_nothing_when_requested_statuses_do_not_exist(self, get_schema, notion_request):
        get_schema.return_value = {
            "properties": {
                "Trạng thái": {
                    "type": "status",
                    "status": {
                        "groups": [{"option_ids": ["not-started"]}],
                        "options": [{"id": "not-started", "name": "Not started"}],
                    },
                }
            }
        }

        pages = bulk_ads_tool.query_ready_pages(
            "database",
            include_exported=False,
            ready_names=["Ready", "To-do"],
        )

        self.assertEqual(pages, [])
        notion_request.assert_not_called()


if __name__ == "__main__":
    unittest.main()
