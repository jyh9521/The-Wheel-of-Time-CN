"""Display-field cleanup must never rename resource identities or control data."""

import json
from pathlib import Path
import unittest
from tools.validate.terminology import load_terms

ROOT = Path(__file__).resolve().parents[1]


class PlayerLabelTests(unittest.TestCase):
    def setUp(self):
        rows = json.loads((ROOT / "locales/zh-CN/strings.json").read_text("utf8"))
        self.rows = {(r["section"], r["key"]): r for r in rows}

    def test_generic_title_is_not_fake_mission_number(self):
        self.assertEqual(
            self.rows["MissionObjectives", "Title"]["translation"], "任务目标"
        )
        self.assertNotIn("XX", self.rows["MissionObjectives", "Title"]["translation"])

    def test_diagnostic_message_does_not_leak_class_name(self):
        row = self.rows["MyrddraalSwordAngreal", "PickupMessage"]
        terms = dict(load_terms(ROOT / "GLOSSARY.md", "中文译名"))
        self.assertIn(terms["Myrddraal"], row["translation"])
        self.assertIn("伤害效果", row["translation"])
        self.assertNotIn("MyrddraalSwordAngreal", row["translation"])
        self.assertEqual(row["section"], "MyrddraalSwordAngreal")

    def test_editor_mnemonic_and_diagnostic_join_spacing(self):
        self.assertTrue(
            self.rows["Windows", "EditCommand"]["translation"].startswith("&")
        )
        self.assertEqual(
            self.rows["WOTPlayer", "CantPlaceResourceStr"]["translation"], "部署失败 "
        )
