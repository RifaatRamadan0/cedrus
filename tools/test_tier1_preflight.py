"""Focused checks for the source gate and region-name compatibility."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.audit_tier1_boxes import inspect
from tools import check_reality


class SourceGateTests(unittest.TestCase):
    def test_box_losses_are_checked_before_fire_filter(self):
        data = b"latitude,longitude,confidence,type\n32,35,90,0\n32,36,90,2\n33,35,90,0\n31,34,90,0\n"
        summary, excluded = inspect(data, (34, 31, 36, 33), "modis")
        self.assertEqual(summary["box_excluded"], 2)
        self.assertEqual(summary["retained_after_box_type0_confidence"], 2)
        self.assertEqual(excluded[0]["type"], "2")

    def test_missing_type_never_counts_as_vegetation(self):
        summary, _ = inspect(b"latitude,longitude,confidence\n32,35,90\n", (34, 31, 36, 33), "modis")
        self.assertEqual(summary["type_counts_before_filters"]["missing"], 1)
        self.assertFalse(summary["type_field_present"])
        self.assertEqual(summary["retained_after_box_type0_confidence"], 0)
        self.assertEqual(summary["monthly_completeness"], "unknown")

    def test_viirs_confidence(self):
        data = b"latitude,longitude,confidence,type\n32,35,n,0\n32,35,h,0\n32,35,l,0\n32,35,n,3\n"
        summary, _ = inspect(data, (34, 31, 36, 33), "viirs-snpp")
        self.assertEqual(summary["retained_after_box_type0_confidence"], 2)

    def test_region_aliases_preserve_names_and_accept_ids(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)
            (path / "regions.json").write_text(json.dumps({"regions": [
                {"id": "la_rioja", "name": "La Rioja area, Argentina"},
                {"id": "lebanon", "name": "Lebanon"},
            ]}), encoding="utf-8")
            with patch.object(check_reality, "WEB", path):
                aliases = check_reality.load_regions()
            self.assertIs(aliases["la_rioja"], aliases["la rioja area, argentina"])
            self.assertEqual(aliases["lebanon"]["id"], "lebanon")
            self.assertNotIn("argentina", aliases)  # national geography is not the area box


if __name__ == "__main__":
    unittest.main()
