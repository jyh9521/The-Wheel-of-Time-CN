import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class TutorialCatalogTests(unittest.TestCase):
    def setUp(self):
        rows = json.loads(
            (ROOT / "locales/zh-CN/strings.json").read_text(encoding="utf-8")
        )
        self.rows = [
            r
            for r in rows
            if r["file"] == "WoTsubtitles.int"
            and r["section"] == "DialogA"
            and r["key"].startswith("Tes_")
        ]

    def test_all_eighty_distinct_keys_translated(self):
        self.assertEqual(len(self.rows), 80)
        self.assertEqual(
            {r["key"] for r in self.rows}, {f"Tes_{n:02}" for n in range(1, 81)}
        )
        self.assertTrue(all(r["translation"] for r in self.rows))

    def test_sources_and_valid_status(self):
        for r in self.rows:
            self.assertEqual(len(r["source_sha256"]), 64)
            self.assertGreater(r["source_length"], 0)
            self.assertIn(r["status"], ["draft", "reviewed"])

    def test_no_manual_padding_or_line_breaks(self):
        for r in self.rows:
            self.assertEqual(r["translation"], r["translation"].strip())
            self.assertFalse(any(c in r["translation"] for c in ["\n", "\r", "\0"]))
