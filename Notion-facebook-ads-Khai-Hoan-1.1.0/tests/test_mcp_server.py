import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import mcp_server


class McpServerTests(unittest.TestCase):
    def test_initialize_and_tool_list_expose_only_safe_planning_actions(self):
        initialized = mcp_server.handle_request(
            {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}
        )
        listed = mcp_server.handle_request(
            {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}
        )

        self.assertEqual(initialized["result"]["serverInfo"]["name"], "khai-hoan-ads-planner")
        names = {item["name"] for item in listed["result"]["tools"]}
        self.assertIn("get_page_posts", names)
        self.assertIn("submit_planner_review", names)
        self.assertNotIn("publish_review", names)
        self.assertNotIn("approve_review", names)
        self.assertNotIn("delete_ad", names)
        submit = next(item for item in listed["result"]["tools"] if item["name"] == "submit_planner_review")
        self.assertFalse(submit["annotations"]["destructiveHint"])
        self.assertFalse(submit["annotations"]["readOnlyHint"])

    def test_stdio_protocol_returns_initialize_and_ignores_notifications(self):
        source = io.StringIO(
            "\n".join(
                [
                    json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}),
                    json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}}),
                    json.dumps({"jsonrpc": "2.0", "id": 2, "method": "ping", "params": {}}),
                ]
            )
            + "\n"
        )
        destination = io.StringIO()

        mcp_server.serve_stdio(source, destination)

        responses = [json.loads(line) for line in destination.getvalue().splitlines()]
        self.assertEqual([item["id"] for item in responses], [1, 2])
        self.assertEqual(responses[1]["result"], {})

    def test_page_posts_are_limited_and_secrets_are_removed(self):
        fake = {
            "page_id": "111",
            "posts": [
                {"permalink_url": f"https://facebook.com/page/posts/{index}"}
                for index in range(3)
            ],
            "summary": {"total": 3, "truncated": False},
            "access_token": "must-not-leak",
        }
        with patch("mcp_server._load_meta_config"), patch(
            "mcp_server.get_page_posts_by_date", return_value=fake
        ):
            result = mcp_server.call_tool(
                "get_page_posts",
                {"since": "2026-07-01", "until": "2026-07-02", "limit": 2},
            )["structuredContent"]

        self.assertEqual(len(result["posts"]), 2)
        self.assertTrue(result["summary"]["limited_for_chat"])
        self.assertNotIn("access_token", result)
        self.assertNotIn("must-not-leak", str(result))

    def test_create_preset_records_audit_without_secret_data(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            audit_path = Path(temp_dir) / "audit.jsonl"
            previous = os.environ.get("MCP_AUDIT_LOG")
            os.environ["MCP_AUDIT_LOG"] = str(audit_path)
            try:
                with patch(
                    "mcp_server.create_preset",
                    return_value={
                        "code": "AUD_TEST",
                        "name": "Test",
                        "access_token": "must-not-leak",
                    },
                ) as create_mock:
                    result = mcp_server.call_tool(
                        "create_audience_preset",
                        {
                            "code": "AUD_TEST",
                            "name": "Test",
                            "summary": "Audience test",
                            "notion_values": {"Giới tính": "Nữ"},
                            "requested_by": "Content A",
                        },
                    )["structuredContent"]
                audit = audit_path.read_text(encoding="utf-8")
            finally:
                if previous is None:
                    os.environ.pop("MCP_AUDIT_LOG", None)
                else:
                    os.environ["MCP_AUDIT_LOG"] = previous

        create_mock.assert_called_once_with(
            "audiences",
            {
                "code": "AUD_TEST",
                "name": "Test",
                "summary": "Audience test",
                "notionValues": {"Giới tính": "Nữ"},
            },
        )
        self.assertTrue(result["saved"])
        self.assertNotIn("access_token", str(result))
        self.assertIn('"actor":"Content A"', audit)
        self.assertNotIn("must-not-leak", audit)

    def test_submit_review_is_pending_only_and_audited(self):
        review = {"id": "a" * 32, "status": "PENDING_REVIEW", "summary": {"ads_count": 2}}
        with tempfile.TemporaryDirectory() as temp_dir:
            audit_path = Path(temp_dir) / "audit.jsonl"
            previous = os.environ.get("MCP_AUDIT_LOG")
            os.environ["MCP_AUDIT_LOG"] = str(audit_path)
            try:
                with patch("mcp_server.submit_review", return_value=(review, False)) as submit_mock:
                    result = mcp_server.call_tool(
                        "submit_planner_review",
                        {
                            "links": ["https://facebook.com/page/posts/1"],
                            "flows": [{"campaign_code": "ENG_BASE"}],
                            "submitted_by": "Content B",
                        },
                    )["structuredContent"]
                audit = audit_path.read_text(encoding="utf-8")
            finally:
                if previous is None:
                    os.environ.pop("MCP_AUDIT_LOG", None)
                else:
                    os.environ["MCP_AUDIT_LOG"] = previous

        self.assertEqual(result["review"]["status"], "PENDING_REVIEW")
        self.assertFalse(result["deduplicated"])
        self.assertEqual(submit_mock.call_args.args[0]["submitted_by"], "Content B")
        self.assertIn('"actor":"Content B"', audit)

    def test_preset_rejects_unknown_or_nested_notion_fields(self):
        with self.assertRaisesRegex(mcp_server.McpToolError, "không được hỗ trợ"):
            mcp_server.call_tool(
                "create_audience_preset",
                {
                    "code": "AUD_TEST",
                    "name": "Test",
                    "summary": "Test",
                    "notion_values": {"META_ACCESS_TOKEN": "secret"},
                    "requested_by": "Content",
                },
            )
        with self.assertRaisesRegex(mcp_server.McpToolError, "chuỗi, số hoặc boolean"):
            mcp_server.call_tool(
                "create_placement_preset",
                {
                    "code": "PLC_TEST",
                    "name": "Test",
                    "summary": "Test",
                    "notion_values": {"Vị trí Facebook": {"feed": True}},
                    "requested_by": "Content",
                },
            )

    def test_validation_errors_are_returned_as_tool_errors(self):
        response = mcp_server.handle_request(
            {
                "jsonrpc": "2.0",
                "id": 7,
                "method": "tools/call",
                "params": {"name": "get_page_posts", "arguments": {"limit": 101}},
            }
        )

        self.assertTrue(response["result"]["isError"])
        self.assertIn("1 đến 100", response["result"]["content"][0]["text"])

        oversized = mcp_server.handle_request(
            {
                "jsonrpc": "2.0",
                "id": 8,
                "method": "tools/call",
                "params": {
                    "name": "preview_planner_plan",
                    "arguments": {"links": ["https://facebook.com/post"], "flows": [{}] * 101},
                },
            }
        )
        self.assertTrue(oversized["result"]["isError"])
        self.assertIn("1 đến 100 cách chạy", oversized["result"]["content"][0]["text"])


if __name__ == "__main__":
    unittest.main()
