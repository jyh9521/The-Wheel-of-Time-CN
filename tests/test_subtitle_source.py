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

    def test_approved_nonempty_override(self):
        import hashlib

        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            a = root / "a/a.int"
            b = root / "b/b.int"
            a.parent.mkdir()
            b.parent.mkdir()
            a.write_text("[A]\nOne=Original\n", encoding="ascii")
            b.write_text("[A]\nOne=Original plus missing speech\n", encoding="ascii")
            rule = dict(
                section="A",
                key="One",
                original_source_sha256=hashlib.sha256(b"Original").hexdigest(),
                reference_source_sha256=hashlib.sha256(
                    b"Original plus missing speech"
                ).hexdigest(),
            )
            r = prepare(
                a, b, root / "out", {"sounds": [dict(section="A", key="One")]}, [rule]
            )
            self.assertEqual(r["changes"][0]["action"], "replace-approved")
            self.assertEqual(
                entries(root / "out/WoTsubtitles.int")[0]["source"],
                "Original plus missing speech",
            )

    def test_wrong_approved_hash_before_write(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            a = root / "a/a.int"
            b = root / "b/b.int"
            a.parent.mkdir()
            b.parent.mkdir()
            a.write_text("[A]\nOne=Original\n", encoding="ascii")
            b.write_text("[A]\nOne=Changed\n", encoding="ascii")
            with self.assertRaisesRegex(ValueError, "fingerprint"):
                prepare(
                    a,
                    b,
                    root / "out",
                    {"sounds": [dict(section="A", key="One")]},
                    [
                        dict(
                            section="A",
                            key="One",
                            original_source_sha256="0" * 64,
                            reference_source_sha256="0" * 64,
                        )
                    ],
                )
            self.assertFalse((root / "out").exists())

    def test_reference_first_complete_union(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            a, b = root / "a/a.int", root / "b/b.int"
            a.parent.mkdir()
            b.parent.mkdir()
            a.write_text(
                "[A]\nOne=Old\nEmpty=Original\nKept=Retained\n", encoding="ascii"
            )
            b.write_text(
                "[A]\nOne=New\nEmpty=\nAdded=Unmatched\nBlank=\n", encoding="ascii"
            )
            result = prepare(
                a, b, root / "out", {"sounds": []}, conflict_policy="prefer-reference"
            )
            values = {
                r["key"]: r["source"] for r in entries(root / "out/WoTsubtitles.int")
            }
            self.assertEqual(
                values,
                {
                    "One": "New",
                    "Empty": "",
                    "Kept": "Retained",
                    "Added": "Unmatched",
                    "Blank": "",
                },
            )
            self.assertEqual(result["conflicts"], [])
            self.assertEqual(
                a.read_text("ascii"), "[A]\nOne=Old\nEmpty=Original\nKept=Retained\n"
            )
