import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from tools.build.source_layer import source_layer, fingerprint, load_rows


class SourceLayerTests(unittest.TestCase):
    def test_default_source_has_no_changes(self):
        with tempfile.TemporaryDirectory() as folder:
            game = Path(folder)
            with source_layer(game, None, {}) as (src, report):
                self.assertEqual(src, game / "System")
                self.assertIsNone(report)

    def test_wrong_external_fingerprint_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            ref = root / "ref.int"
            ref.write_bytes(b"wrong")
            with self.assertRaisesRegex(ValueError, "fingerprint"):
                with source_layer(
                    root, ref, dict(reference_sha256="0" * 64, reference_size=5)
                ):
                    pass

    def test_prepared_source_and_temporary_cleanup(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            game = root / "game"
            (game / "System").mkdir(parents=True)
            (game / "Sounds").mkdir()
            original = b"[A]\nOne=\n"
            ref = root / "ref.int"
            ref.write_bytes(b"[A]\nOne=Recovered\n")
            (game / "System/WoTsubtitles.int").write_bytes(original)
            (game / "Sounds/A.uax").write_bytes(b"fixture")
            manifest = dict(
                id="fixture",
                file="WoTsubtitles.int",
                reference_sha256=hashlib.sha256(ref.read_bytes()).hexdigest(),
                reference_size=ref.stat().st_size,
                expected_merged_sha256=hashlib.sha256(
                    b'[A]\nOne="Recovered"\n'
                ).hexdigest(),
                package_inputs=[
                    dict(
                        file="Sounds/A.uax",
                        size=7,
                        sha256=hashlib.sha256(b"fixture").hexdigest(),
                    )
                ],
            )
            with patch("tools.build.source_layer.Package") as package:
                package.return_value.records.return_value = [
                    dict(class_name="Sound", path="One")
                ]
                with source_layer(game, ref, manifest) as (src, report):
                    self.assertEqual(
                        (src / "WoTsubtitles.int").read_bytes(),
                        b'[A]\nOne="Recovered"\n',
                    )
                    self.assertEqual(report["id"], "fixture")
                self.assertFalse(src.exists())
            self.assertEqual((game / "System/WoTsubtitles.int").read_bytes(), original)

    def test_locale_path_escape_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaisesRegex(ValueError, "escapes"):
                load_rows(Path(folder), {"subtitle_rows": "../elsewhere.json"}, {})

    def test_row_source_identity_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "rows.json").write_text(
                json.dumps([dict(source_layer="wrong", file="WoTsubtitles.int")])
            )
            with self.assertRaisesRegex(ValueError, "identity"):
                load_rows(
                    root,
                    {"subtitle_rows": "rows.json"},
                    {"id": "expected", "file": "WoTsubtitles.int"},
                )

    def test_active_english_punctuation_and_translation(self):
        from tools.build.source_layer import active_subtitle_texts

        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder)
            (source / "WoTsubtitles.int").write_text(
                "[A]\nOne=Don’t\nTwo=Recovered\n", encoding="utf-8-sig"
            )
            rows = [
                dict(
                    file="WoTsubtitles.int",
                    section="A",
                    key="Two",
                    occurrence=1,
                    translation="恢复",
                )
            ]
            self.assertEqual(
                active_subtitle_texts(source, rows, ["WoTsubtitles.int"]),
                ["Don’t", "恢复"],
            )

    def test_composed_override_preserves_base(self):
        from tools.build.source_layer import compose_rows

        base = [
            dict(
                file="S.int",
                section="A",
                key="One",
                occurrence=1,
                source_sha256="old",
                translation="before",
            )
        ]
        replacement = dict(base[0], source_sha256="new", translation="after")
        manifest = dict(
            file="S.int",
            approved_overrides=[
                dict(
                    section="A",
                    key="One",
                    original_source_sha256="old",
                    reference_source_sha256="new",
                )
            ],
        )
        result = compose_rows(base, [], [replacement], manifest)
        self.assertEqual(result[0]["translation"], "after")
        self.assertEqual(base[0]["translation"], "before")

    def test_unapproved_translation_override_rejected(self):
        from tools.build.source_layer import compose_rows

        row = dict(
            file="S.int", section="A", key="One", occurrence=1, source_sha256="old"
        )
        with self.assertRaisesRegex(ValueError, "Unapproved"):
            compose_rows([row], [], [row], dict(file="S.int"))

    def test_override_translation_source_fingerprint_rejected(self):
        from tools.build.source_layer import compose_rows

        row = dict(
            file="S.int", section="A", key="One", occurrence=1, source_sha256="old"
        )
        manifest = dict(
            file="S.int",
            approved_overrides=[
                dict(
                    section="A",
                    key="One",
                    original_source_sha256="old",
                    reference_source_sha256="new",
                )
            ],
        )
        with self.assertRaisesRegex(ValueError, "fingerprint"):
            compose_rows([row], [], [row], manifest)
