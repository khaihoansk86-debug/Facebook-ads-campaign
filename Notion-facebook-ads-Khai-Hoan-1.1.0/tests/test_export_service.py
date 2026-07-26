import csv
import tempfile
import unittest
from pathlib import Path

from ads_core.export_service import ExportValidationError, export_selected_pages, list_export_candidates
from ads_core.facebook_csv import write_facebook_csv


class ExportServiceTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.sample = self.root / "sample.csv"
        write_facebook_csv(self.sample, ["Ad Name", "Campaign Name"], [{"Ad Name": "Mẫu", "Campaign Name": "Mẫu"}])
        self.pages = [
            {"id": "page-1", "url": "https://notion.so/1", "properties": {"mock": 1}},
            {"id": "page-2", "url": "https://notion.so/2", "properties": {"mock": 2}},
        ]

    def tearDown(self):
        self.temp_dir.cleanup()

    def query(self, *_args, **_kwargs):
        return list(self.pages)

    def test_lists_safe_candidate_summaries(self):
        values = lambda page: {
            "Tên chiến dịch / bài ads": f"Bài {page['id']}",
            "Trạng thái": "Ready",
            "Link bài viết": "https://facebook.com/a",
        }
        result = list_export_candidates("database", self.query, values)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["status"], "Sẵn sàng")

    def test_exports_only_selected_page_and_marks_it(self):
        marked = []

        def build_rows(pages, headers, _template, _mapping, _samples):
            return [{"Ad Name": page["id"], "Campaign Name": "Chiến dịch"} for page in pages]

        result = export_selected_pages(
            database_id="database",
            selected_page_ids=["page-2"],
            sample_csv=self.sample,
            template_row_index=0,
            output_dir=self.root / "exports",
            mapping={},
            query_func=self.query,
            build_rows_func=build_rows,
            mark_exported_func=lambda page_id, _props: marked.append(page_id),
        )
        self.assertEqual(result["count"], 1)
        self.assertEqual(marked, ["page-2"])
        with Path(result["output"]).open("r", encoding="utf-16", newline="") as handle:
            rows = list(csv.DictReader(handle, delimiter="\t"))
        self.assertEqual(rows[0]["Ad Name"], "page-2")

    def test_rejects_page_that_is_no_longer_eligible(self):
        with self.assertRaisesRegex(ExportValidationError, "không còn đủ điều kiện"):
            export_selected_pages(
                database_id="database",
                selected_page_ids=["missing-page"],
                sample_csv=self.sample,
                template_row_index=0,
                output_dir=self.root / "exports",
                mapping={},
                query_func=self.query,
                build_rows_func=lambda *_args: [],
                mark_exported_func=lambda *_args: None,
            )


if __name__ == "__main__":
    unittest.main()
