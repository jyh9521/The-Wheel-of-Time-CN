import copy
import hashlib
import importlib
import tempfile
import unittest
from pathlib import Path

module = importlib.import_module("tools.import.int_files")


class SourcePreflightTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.source = Path(self.directory.name)
        (self.source / "Sample.int").write_bytes(b"[Menu]\r\nTitle=New Game\r\n")
        self.row = {
            "file": "Sample.int",
            "section": "Menu",
            "key": "Title",
            "occurrence": 1,
            "source_sha256": hashlib.sha256(b"New Game").hexdigest(),
            "source_length": 8,
            "tokens": [],
            "translation": "新游戏",
        }

    def test_preflight_read_only(self):
        before = (self.source / "Sample.int").read_bytes()
        self.assertEqual(module.verify_sources(self.source, [self.row]), 1)
        self.assertEqual((self.source / "Sample.int").read_bytes(), before)
        self.assertEqual(len(list(self.source.iterdir())), 1)

    def test_source_hash_mismatch(self):
        self.row["source_sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "Source changed"):
            module.verify_sources(self.source, [self.row])

    def test_source_length_mismatch(self):
        self.row["source_length"] = 9
        with self.assertRaisesRegex(ValueError, "Source length"):
            module.verify_sources(self.source, [self.row])

    def test_source_token_metadata_mismatch(self):
        self.row["tokens"] = ["%s"]
        with self.assertRaisesRegex(ValueError, "Source token"):
            module.verify_sources(self.source, [self.row])

    def test_missing_id(self):
        self.row["key"] = "Missing"
        with self.assertRaisesRegex(ValueError, "Source ID missing"):
            module.verify_sources(self.source, [self.row])

    def test_untranslated_source_is_checked(self):
        self.row["translation"] = ""
        self.row["source_length"] = 1
        with self.assertRaises(ValueError):
            module.verify_sources(self.source, [self.row])

    def test_all_sources_checked_before_output(self):
        invalid = copy.deepcopy(self.row)
        invalid["file"] = "Other.int"
        (self.source / "Other.int").write_bytes(b"[Menu]\nTitle=Other\n")
        out = self.source / "output"
        config = {
            "encoding": "utf-16le-bom",
            "validation": {"max_characters": 4096},
            "subtitle_timing": "preserve-source-length",
        }
        with self.assertRaises(ValueError):
            module.import_rows(
                self.source, [self.row, invalid], out, config, {"subtitle_files": []}
            )
        self.assertFalse(out.exists())
