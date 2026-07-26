import tempfile
import unittest
from pathlib import Path

from ads_core.planner_catalog import save_planner_bundles
from ads_core.preset_service import (
    PresetValidationError,
    create_preset,
    list_presets,
    update_preset,
)


class PresetServiceTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.path = Path(self.temp_dir.name) / "planner.json"
        save_planner_bundles({"audiencePresets": [], "placementPresets": [], "budgetPresets": []}, self.path)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_create_and_update_audience(self):
        created = create_preset(
            "audiences",
            {
                "code": "aud_new",
                "name": "Khách mới",
                "summary": "Tệp rộng",
                "notionValues": {"Tuổi min": 18, "Trống": ""},
            },
            self.path,
        )
        self.assertEqual(created["code"], "AUD_NEW")
        self.assertEqual(len(list_presets("audiences", self.path)), 1)

        updated = update_preset(
            "audiences",
            "AUD_NEW",
            {**created, "name": "Khách mới đã sửa", "notionValues": {"Tuổi min": 21}},
            self.path,
        )
        self.assertEqual(updated["name"], "Khách mới đã sửa")
        self.assertEqual(updated["notionValues"]["Tuổi min"], 21)

    def test_rejects_duplicate_and_invalid_kind(self):
        payload = {"code": "AUD_NEW", "name": "Khách mới", "notionValues": {}}
        create_preset("audiences", payload, self.path)
        with self.assertRaises(PresetValidationError):
            create_preset("audiences", payload, self.path)
        with self.assertRaises(PresetValidationError):
            list_presets("unknown", self.path)


if __name__ == "__main__":
    unittest.main()
