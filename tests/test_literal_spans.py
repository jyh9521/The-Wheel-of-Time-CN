"""Reviewed literal-span annotations keep source tokens and unknown codes intact."""

import copy
import hashlib
import importlib
from pathlib import Path
import tempfile
import unittest
from tools.extract.int_files import tokens, translation_tokens

importer = importlib.import_module("tools.import.int_files")


class LiteralSpanTests(unittest.TestCase):
    def row(self):
        source = "A @word@ and %s {0}"
        return dict(
            file="sample.int",
            section="Item",
            key="Description",
            occurrence=1,
            source_sha256=hashlib.sha256(source.encode()).hexdigest(),
            source_length=len(source),
            tokens=tokens(source),
            translation="甲 @词@ 与 %s {0}",
            literal_token_translations=[dict(source="@word@", translation="@词@")],
            markup_delimiter_count=2,
        )

    def test_literal_with_genuine_controls(self):
        row = self.row()
        self.assertEqual(translation_tokens(row), row["tokens"])
        self.assertEqual(
            importer.validate_rows(
                [row],
                dict(encoding="utf-16le-bom", validation=dict(max_characters=100)),
            ),
            0,
        )

    def test_unchanged_default_protection(self):
        row = self.row()
        row.pop("literal_token_translations")
        self.assertNotEqual(translation_tokens(row), row["tokens"])

    def test_missing_extra_and_changed_controls_rejected(self):
        for value in [
            "甲 @词 与 %s {0}",
            "甲 @词@ @词@ 与 %s {0}",
            "甲 @词@ 与 %d {0}",
            "甲 @词@ @x@ 与 %s {0}",
        ]:
            row = self.row()
            row["translation"] = value
            with self.assertRaises(ValueError):
                importer.validate_rows(
                    [row],
                    dict(encoding="utf-16le-bom", validation=dict(max_characters=100)),
                )

    def test_annotation_cannot_contain_control_or_unknown_source(self):
        for source, target in [
            ("@other@", "@词@"),
            ("@word@", "@%s@"),
            ("@word@", "词"),
        ]:
            row = self.row()
            row["literal_token_translations"] = [
                dict(source=source, translation=target)
            ]
            with self.assertRaises(ValueError):
                translation_tokens(row)

    def test_real_source_preflight_and_hash_guard(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "sample.int"
            path.write_text("[Item]\nDescription=A @word@ and %s {0}\n", "ascii")
            row = self.row()
            self.assertEqual(importer.verify_sources(tmp, [row]), 1)
            bad = copy.deepcopy(row)
            bad["markup_delimiter_count"] = 4
            with self.assertRaises(ValueError):
                importer.verify_sources(tmp, [bad])
            path.write_text("[Item]\nDescription=A @changed@ and %s {0}\n", "ascii")
            with self.assertRaises(ValueError):
                importer.verify_sources(tmp, [row])
