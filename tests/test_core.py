import copy
import importlib
import json
import tempfile
import unittest
from pathlib import Path
from src.patch.delta import create, apply, sha
from install import transaction, targets
from tools.extract.int_files import decode, encode, entries, tokens
from tools.pack.ue1 import Reader, ci

importer = importlib.import_module("tools.import.int_files")
CONFIG = {
    "encoding": "utf-16le-bom",
    "validation": {"max_characters": 100},
    "subtitle_timing": "preserve-source-length",
}


def row(text="New Game", translation="新游戏"):
    return {
        "file": "Sample.int",
        "section": "Menu",
        "key": "Title",
        "occurrence": 1,
        "source_sha256": sha(text.encode()),
        "tokens": tokens(text),
        "translation": translation,
        "source_length": len(text),
    }


class CoreTests(unittest.TestCase):
    def test_compact_indices(self):
        for value in (0, 1, -1, 63, 64, -64, 8192, 2**30 - 1):
            self.assertEqual(Reader(ci(value)).idx(), value)

    def test_unicode_encoding(self):
        for encoding in ("utf-16le-bom", "utf-16be-bom", "utf-8-bom"):
            self.assertEqual(
                decode(encode("中文 日本語 한국어", encoding)),
                ("中文 日本語 한국어", encoding),
            )

    def test_tokens(self):
        s = r"{0} %s %d $n ^ab <tag> \0 \unknown %f=2 %b @Name@"
        self.assertEqual(
            tokens(s),
            [
                "{0}",
                "%s",
                "%d",
                "$n",
                "^ab",
                "<tag>",
                r"\0",
                r"\unknown",
                "%f=2",
                "%b",
                "@Name@",
            ],
        )

    def test_duplicate_id_rejected(self):
        with self.assertRaises(ValueError):
            importer.validate_rows([row(), row()], CONFIG)

    def test_token_change_rejected(self):
        with self.assertRaises(ValueError):
            importer.validate_rows([row("Hello %s", "您好")], CONFIG)

    def test_non_bmp_rejected(self):
        with self.assertRaises(ValueError):
            importer.validate_rows([row(translation="😀")], CONFIG)

    def test_literal_newline_rejected(self):
        with self.assertRaises(ValueError):
            importer.validate_rows([row(translation="a\nb")], CONFIG)

    def test_character_limit(self):
        with self.assertRaises(ValueError):
            importer.validate_rows([row(translation="a" * 101)], CONFIG)

    def test_byte_limit(self):
        r = row()
        r["max_bytes"] = 6
        with self.assertRaises(ValueError):
            importer.validate_rows([r], CONFIG)

    def test_associated_translations(self):
        a = row()
        a["sync_group"] = "menu"
        b = copy.deepcopy(a)
        b["key"] = "Other"
        b["translation"] = "別文"
        with self.assertRaises(ValueError):
            importer.validate_rows([a, b], CONFIG)

    def test_unknown_control_preserved(self):
        a = row("Value %unknown", "值 %unknown")
        self.assertEqual(importer.validate_rows([a], CONFIG), 0)
        a["translation"] = "值"
        with self.assertRaises(ValueError):
            importer.validate_rows([a], CONFIG)

    def test_subtitle_length_padding(self):
        with tempfile.TemporaryDirectory() as d:
            src = Path(d)
            (src / "Sample.int").write_bytes(b"[Menu]\r\nTitle=New Game\r\n")
            out = src / "output"
            importer.import_rows(
                src, [row()], out, CONFIG, {"subtitle_files": ["Sample.int"]}
            )
            value = entries(out / "Sample.int")[0]["source"]
            self.assertEqual(value, "新游戏" + " " * 5)

    def test_public_metadata_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            src = Path(d)
            (src / "Sample.int").write_bytes(b"[Public]\nObject=Class\n")
            r = row("Class", "类")
            r["section"] = "Public"
            r["key"] = "Object"
            with self.assertRaises(ValueError):
                importer.import_rows(
                    src, [r], src / "out", CONFIG, {"subtitle_files": []}
                )

    def test_bmp_font_character_scan(self):
        from tools.font.build_font import characters

        self.assertEqual(characters(["日中日", "한"]), sorted(set("日中한")))
        with self.assertRaises(ValueError):
            characters(["😀"])

    def test_missing_font_glyph(self):
        from unittest.mock import patch, MagicMock
        from tools.validate.fonts import check_font

        mock = MagicMock()
        mock.__enter__.return_value.getBestCmap.return_value = {ord("A"): "A"}
        with patch("tools.validate.fonts.TTFont", return_value=mock):
            with self.assertRaises(ValueError):
                check_font([row()], Path("fixture.ttf"), {"baseline_anchor": "A"})

    def test_corrupt_delta_copy_range(self):
        d = create(b"a" * 1024, b"a" * 1024)
        d["operations"][0]["copy"] = -1
        with self.assertRaises(ValueError):
            apply(b"a" * 1024, d)

    def test_literal_size_bomb(self):
        d = create(b"", b"a" * 100)
        d["operations"][0]["size"] = 1
        with self.assertRaises(ValueError):
            apply(b"", d)

    def test_import_preserves_unrelated_entries(self):
        with tempfile.TemporaryDirectory() as d:
            src = Path(d) / "source"
            src.mkdir()
            dst = Path(d) / "output"
            b = b";comment\r\n[Menu]\r\nTitle=New Game\r\nOther=ASCII\r\n"
            (src / "Sample.int").write_bytes(b)
            importer.import_rows(src, [row()], dst, CONFIG, {"subtitle_files": []})
            self.assertEqual((src / "Sample.int").read_bytes(), b)
            self.assertEqual(
                decode((dst / "Sample.int").read_bytes())[0],
                ";comment\r\n[Menu]\r\nTitle=新游戏\r\nOther=ASCII\r\n",
            )

    def test_source_changed_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)
            (p / "Sample.int").write_bytes(b"[Menu]\nTitle=Changed\n")
            with self.assertRaises(ValueError):
                importer.import_rows(
                    p, [row()], p / "out", CONFIG, {"subtitle_files": []}
                )

    def test_duplicate_occurrence(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "Sample.int"
            p.write_bytes(b"[Menu]\nTitle=A\nTitle=B\n")
            self.assertEqual([r["occurrence"] for r in entries(p)], [1, 2])

    def test_multilingual_configuration(self):
        for s in ("新游戏", "新遊戲", "ニューゲーム", "새 게임"):
            self.assertEqual(importer.validate_rows([row(translation=s)], CONFIG), 0)

    def test_delta_roundtrip(self):
        for b, m in (
            (b"", b"abc"),
            (b"abc", b""),
            (b"123" * 1000, b"123" * 500 + b"changed" + b"123" * 500),
        ):
            self.assertEqual(apply(b, create(b, m)), m)

    def test_delta_wrong_original(self):
        with self.assertRaises(ValueError):
            apply(b"wrong", create(b"original", b"modified"))

    def test_delta_corruption(self):
        delta = create(b"original", b"modified")
        delta["modified_sha256"] = "0" * 64
        with self.assertRaises(ValueError):
            apply(b"original", delta)

    def test_install_rollback(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)
            (p / "System").mkdir()
            f = p / "System/Sample.int"
            f.write_bytes(b"original")
            bundle = p / "bundle.json"
            bundle.write_text(
                json.dumps(
                    {
                        "format": "localization-bundle-v1",
                        "files": {
                            "System/Sample.int": create(b"original", b"modified")
                        },
                    }
                )
            )
            transaction("apply", bundle, p)
            transaction("verify", bundle, p)
            self.assertEqual(f.read_bytes(), b"modified")
            transaction("restore", bundle, p)
            self.assertEqual(f.read_bytes(), b"original")

    def test_installer_preflight_atomic(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)
            (p / "System").mkdir()
            (p / "System/A.int").write_bytes(b"a")
            (p / "System/B.int").write_bytes(b"unknown")
            bundle = p / "b.json"
            bundle.write_text(
                json.dumps(
                    {
                        "format": "localization-bundle-v1",
                        "files": {
                            "System/A.int": create(b"a", b"A"),
                            "System/B.int": create(b"b", b"B"),
                        },
                    }
                )
            )
            with self.assertRaises(ValueError):
                transaction("apply", bundle, p)
            self.assertEqual((p / "System/A.int").read_bytes(), b"a")

    def test_path_traversal(self):
        for name in (
            "../System/A.int",
            "System/../../A.int",
            "System/A.exe",
            "System/C:/A.int",
        ):
            with self.assertRaises(ValueError):
                targets(
                    Path.cwd(),
                    {"format": "localization-bundle-v1", "files": {name: {}}},
                )

    def test_restore_changed_resource_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)
            (p / "System").mkdir()
            f = p / "System/A.int"
            f.write_bytes(b"a")
            bundle = p / "b.json"
            bundle.write_text(
                json.dumps(
                    {
                        "format": "localization-bundle-v1",
                        "files": {"System/A.int": create(b"a", b"A")},
                    }
                )
            )
            transaction("apply", bundle, p)
            f.write_bytes(b"user edit")
            with self.assertRaises(ValueError):
                transaction("restore", bundle, p)
            self.assertEqual(f.read_bytes(), b"user edit")
