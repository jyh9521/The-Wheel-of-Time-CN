import copy
import json
import tempfile
import unittest
from pathlib import Path

from tools.validate.qa_policy import load_policy, make_plan, sweep_count


class MenuSweepTests(unittest.TestCase):
    def test_default_preserves_single_frame(self):
        self.assertEqual(sweep_count(load_policy(), "options", False), 1)

    def test_configured_menu(self):
        self.assertEqual(sweep_count(load_policy(), "options", True), 11)

    def test_unconfigured_view_rejected(self):
        with self.assertRaises(ValueError):
            sweep_count(load_policy(), "inventory", True)

    def test_language_neutral_plan(self):
        probes = make_plan(load_policy(), "ko-KR")["probes"]
        self.assertEqual(len(probes), 10)
        for probe in probes:
            self.assertEqual("--sweep" in probe["argv"], probe["view"] == "options")

    def test_invalid_counts_rejected(self):
        for count in (0, 65, True, "11"):
            policy = copy.deepcopy(load_policy())
            policy["menu_item_counts"] = {"options": count}
            with tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / "policy.json"
                path.write_text(json.dumps(policy), encoding="utf8")
                with self.assertRaises(ValueError):
                    load_policy(path)

    def test_unknown_view_rejected(self):
        policy = copy.deepcopy(load_policy())
        policy["menu_item_counts"] = {"unknown": 2}
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "policy.json"
            path.write_text(json.dumps(policy), encoding="utf8")
            with self.assertRaises(ValueError):
                load_policy(path)
