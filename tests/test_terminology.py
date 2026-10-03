import unittest
from pathlib import Path
import tempfile
from tools.validate.terminology import load_terms, matches, audit


class TerminologyTests(unittest.TestCase):
    def test_sole_confirmed_table(self):
        with tempfile.TemporaryDirectory() as folder:
            p = Path(folder) / "GLOSSARY.md"
            p.write_text(
                "## 术语表\n| English | 中文译名 |\n|---|---|\n| Creator | **创世主** |\n---\n## 待确认术语\n| English / 来源 | 当前唯一草稿 |\n|---|---|\n| Elayna | 伊莱娜 |\n",
                "utf8",
            )
            self.assertEqual(load_terms(p, "中文译名"), [("Creator", "创世主")])

    def test_longest_apostrophes_plurals_and_identifier_protection(self):
        terms = [
            ("angreal", "法器"),
            ("ter'angreal", "特法器"),
            ("Trolloc", "兽魔人"),
            ("channel", "导引"),
            ("channeler", "导引者"),
        ]
        self.assertEqual(
            matches("Ter’angreals Trollocs channeler @Trolloc@", terms),
            [("ter'angreal", "特法器"), ("channeler", "导引者"), ("Trolloc", "兽魔人")],
        )
        self.assertEqual(matches("rectangular angreal_name", terms), [])

    def test_mismatch_and_correction(self):
        with tempfile.TemporaryDirectory() as folder:
            p = Path(folder)
            (p / "A.int").write_text("[A]\nOne=The Creator, save me!\n", "utf8")
            rows = [
                dict(
                    file="A.int",
                    section="A",
                    key="One",
                    occurrence=1,
                    translation="造物主，救救我！",
                )
            ]
            self.assertEqual(
                len(audit(rows, p, [("Creator", "创世主")])["findings"]), 1
            )
            rows[0]["translation"] = "创世主，救救我！"
            self.assertEqual(audit(rows, p, [("Creator", "创世主")])["findings"], [])

    def test_context_exception_requires_exact_source(self):
        import hashlib

        with tempfile.TemporaryDirectory() as folder:
            p = Path(folder)
            source = "Channel the invaders."
            (p / "A.int").write_text("[A]\nOne=" + source + "\n", "utf8")
            rows = [
                dict(
                    file="A.int",
                    section="A",
                    key="One",
                    occurrence=1,
                    translation="引入敌人。",
                )
            ]
            rule = dict(
                identity=("A.int", "A", "One", 1),
                term="channel",
                source_sha256=hashlib.sha256(source.encode()).hexdigest(),
                reason="ordinary verb",
            )
            self.assertEqual(
                audit(rows, p, [("channel", "导引")], [rule])["findings"], []
            )
            rule["source_sha256"] = "0" * 64
            with self.assertRaisesRegex(ValueError, "source changed"):
                audit(rows, p, [("channel", "导引")], [rule])
