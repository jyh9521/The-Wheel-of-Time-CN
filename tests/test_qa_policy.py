import copy
import json
import tempfile
import unittest
from pathlib import Path
from tools.validate.qa_policy import load_policy, make_plan


class QAPolicyTests(unittest.TestCase):
    def test_recommends_1080p(self):
        self.assertEqual(load_policy()["recommended"], [1920, 1080])

    def test_4k_not_active(self):
        p = load_policy()
        self.assertNotIn([3840, 2160], p["active_resolutions"])
        self.assertIn([3840, 2160], p["known_issue_resolutions"])

    def test_plan_recommended_first_without_launch(self):
        plan = make_plan(load_policy(), "ja-JP")
        self.assertFalse(plan["launches_game"])
        self.assertEqual(len(plan["probes"]), 18)
        self.assertEqual(plan["probes"][0]["resolution"], [1920, 1080])
        self.assertIn("build/ja-JP", plan["probes"][0]["argv"])
        self.assertTrue(all(p["resolution"] != [3840, 2160] for p in plan["probes"]))

    def test_original_modified_pairs(self):
        probes = make_plan(load_policy(), "zh-CN")["probes"]
        for i in range(0, len(probes), 2):
            self.assertTrue(probes[i]["original"])
            self.assertFalse(probes[i + 1]["original"])
            self.assertEqual(probes[i]["resolution"], probes[i + 1]["resolution"])

    def test_invalid_locale(self):
        with self.assertRaises(ValueError):
            make_plan(load_policy(), "../invalid")

    def test_excluded_resolution_cannot_be_active(self):
        p = copy.deepcopy(load_policy())
        p["active_resolutions"].append([3840, 2160])
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "policy.json"
            path.write_text(json.dumps(p), "utf8")
            with self.assertRaises(ValueError):
                load_policy(path)
