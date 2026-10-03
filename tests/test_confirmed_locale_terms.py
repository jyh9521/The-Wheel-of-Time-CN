"""Regression checks for the zh-CN maintainer-confirmed terminology batch."""

import json
from pathlib import Path
import unittest
from tools.validate.terminology import load_terms, load_exceptions, matches

ROOT = Path(__file__).resolve().parents[1]


class ConfirmedLocaleTermsTests(unittest.TestCase):
    def setUp(self):
        self.terms = dict(load_terms(ROOT / "GLOSSARY.md", "中文译名"))
        self.rows = []
        for name in ["strings", "subtitles", "subtitle-overrides"]:
            self.rows.extend(
                json.loads((ROOT / f"locales/zh-CN/{name}.json").read_text("utf8"))
            )

    def text(self, section, key):
        found = [
            r["translation"]
            for r in self.rows
            if r["section"] == section and r["key"] == key
        ]
        self.assertTrue(found)
        return found

    def test_named_ability_titles_use_sole_glossary(self):
        for r in self.rows:
            if r["file"] == "Angreal.int" and r["key"] == "Title":
                # The list intentionally contains identities, not a parallel translation map.
                if r["section"] in {
                    "AngrealInvAirBurst",
                    "AngrealInvLightGlobe",
                    "AngrealInvReflect",
                    "AngrealInvFireball",
                    "AngrealInvFireShield",
                    "AngrealInvSpecial",
                }:
                    continue
                self.assertIn(r["translation"], self.terms.values(), r["section"])
        self.assertEqual(self.text("ViewCam", "ItemName"), [self.terms["ViewCam"]])
        self.assertEqual(self.text("Hound", "MenuName"), [self.terms["Hound"]])
        self.assertEqual(self.text("Hound", "TeamDescription"), [self.terms["Hound"]])
        for section, term in [
            ("LegionStompAngrealInv", "Legion Stomp"),
            ("LegionInvSeeker", "LegionSeeker"),
            ("MinionInventory", "Minion"),
            ("LegionInventory", "Legion"),
        ]:
            self.assertEqual(self.text(section, "Title"), [self.terms[term]])

    def test_locked_countermeasures(self):
        for english, target in [
            ("Sever", "隔断"),
            ("Fork", "分流"),
            ("Unravel", "解构"),
            ("Aura of Unraveling", "解构领域"),
            ("Shift", "瞬移"),
        ]:
            self.assertEqual(self.terms[english], target)
        self.assertEqual(
            matches("Aura of Unraveling", list(self.terms.items())),
            [("Aura of Unraveling", "解构领域")],
        )

    def test_sister_context(self):
        for section, key in [
            ("DialogA", "Aes_16"),
            ("DialogA", "Evl_05"),
            ("DialogA", "War_11"),
            ("WarderA", "War_ShowRespect1"),
        ]:
            for text in self.text(section, key):
                self.assertIn("姐妹", text)
                self.assertNotIn("两仪师", text)
        for key in ["Tes_63", "Tes_73", "Tes_74"]:
            for text in self.text("DialogA", key):
                self.assertIn("两仪师", text)
        self.assertEqual(
            self.text("SisterInventory", "Title"), [self.terms["Aes Sedai"]]
        )
        self.assertNotIn("Sister", self.terms)

    def test_artifact_referent_and_weaves(self):
        self.assertNotIn("artifact", self.terms)
        for key in [
            "Tes_29",
            "Tes_36",
            "Tes_47",
            "Tes_48",
            "Tes_50",
            "Tes_51",
            "Tes_52",
            "Tes_54",
        ]:
            for text in self.text("DialogA", key):
                self.assertIn("特法器", text)
        self.assertIn("器物", self.text("Seal", "Description")[0])
        self.assertNotIn("特法器", self.text("Seal", "Description")[0])
        self.assertIn("魔法器物", self.text("AngrealInvSpecial", "Description")[0])
        for section, element in [
            ("AngrealInvFireShield", "Fire"),
            ("AngrealInvAirShield", "Air"),
            ("AngrealInvWaterShield", "Water"),
            ("AngrealInvEarthShield", "Earth"),
            ("AngrealInvSpiritShield", "Spirit"),
        ]:
            self.assertIn(
                self.terms["weaves of " + element], self.text(section, "Description")[0]
            )

    def test_remaining_names_and_test_marker_are_resolved(self):
        import re

        names = [
            "Chosen",
            "Cuendillar",
            "Manetherendrelle",
            "Machin Shin",
            "Mountains of Mist",
            "Cerist",
            "Sephraem",
            "Halfmen",
            "Bornhald",
            "Elaida",
            "The Hand of the Light",
            "The Hand that digs out Truth",
        ]
        for name in names:
            self.assertIn(name, self.terms)
            pattern = re.compile(
                r"(?<![A-Za-z0-9_])" + re.escape(name) + r"(?![A-Za-z0-9_])", re.I
            )
            for row in self.rows:
                self.assertIsNone(
                    pattern.search(row["translation"]),
                    (name, row["section"], row["key"]),
                )
        self.assertNotIn("END-123", " ".join(row["translation"] for row in self.rows))
        for key in ["Myr_14", "Myr_25"]:
            self.assertIn(self.terms["Chosen"], self.text("DialogA", key)[0])
        self.assertIn("被选中", self.text("WarderInventory", "Description")[0])

    def test_protected_fragments_and_normal_word_exceptions(self):
        for section, token in [
            ("AngrealInvDistantEye", "@忘记@"),
            ("AngrealInvMinion", "@普通士兵@"),
        ]:
            self.assertIn(token, self.text(section, "Description")[0])
        self.assertIn(
            "@那些编织就……消失了。@", self.text("AngrealInvAbsorb", "Quote")[0]
        )
        exceptions = load_exceptions(ROOT / "GLOSSARY.md")
        self.assertTrue(
            any(
                e["identity"][1] == "AngrealInvExpWard" and e["term"] == "Unravel"
                for e in exceptions
            )
        )
        self.assertTrue(
            any(
                e["identity"][1] == "AngrealInvTaint" and e["term"] == "Taint"
                for e in exceptions
            )
        )


if __name__ == "__main__":
    unittest.main()
