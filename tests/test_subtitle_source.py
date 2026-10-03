import importlib
import tempfile
import unittest
from pathlib import Path
from tools.extract.int_files import entries

prepare = importlib.import_module("tools.import.subtitle_source").prepare


class SubtitleSourceTests(unittest.TestCase):
    def test_conservative_merge(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            a = root / "original/a.int"
            b = root / "reference/b.int"
            a.parent.mkdir()
            b.parent.mkdir()
            a.write_text("[A]\nOne=Original\nTwo=\nKept=\n", encoding="ascii")
            b.write_text(
                "[A]\nOne=Changed\nTwo=Recovered\nAdded=New\nUnknown=Bad\n",
                encoding="ascii",
            )
            inv = {
                "sounds": [dict(section="A", key=k) for k in ["One", "Two", "Added"]]
            }
            result = prepare(a, b, root / "out", inv)
            self.assertEqual(result["total"], 4)
            self.assertEqual(len(result["changes"]), 2)
            self.assertEqual(len(result["conflicts"]), 1)
            self.assertEqual(len(result["unsupported"]), 1)
            values = {
                r["key"]: r["source"] for r in entries(root / "out/WoTsubtitles.int")
            }
            self.assertEqual(
                values,
                {"One": "Original", "Two": "Recovered", "Kept": "", "Added": "New"},
            )
            with self.assertRaises(ValueError):
                prepare(a, b, a.parent, inv)

    def test_duplicates_rejected_before_output(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            a = root / "original/a.int"
            b = root / "reference/b.int"
            a.parent.mkdir()
            b.parent.mkdir()
            a.write_text("[A]\nOne=\n", encoding="ascii")
            b.write_text("[A]\nOne=First\none=Second\n", encoding="ascii")
            with self.assertRaises(ValueError):
                prepare(a, b, root / "out", {"sounds": []})
            self.assertFalse((root / "out").exists())
