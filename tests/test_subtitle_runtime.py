import json
import tempfile
import unittest
from pathlib import Path
from tools.build.subtitle_runtime import caption_at, validate_cues, manage


class SubtitleRuntimeTests(unittest.TestCase):
    def test_independent_actor_clock_wiring(self):
        root = Path(__file__).resolve().parents[1]
        player = (root / "src/runtime/LocaleRuntime/Classes/LocalePlayer.uc").read_text(
            "utf8"
        )
        clock = (
            root / "src/runtime/LocaleRuntime/Classes/LocaleSubtitleClock.uc"
        ).read_text("utf8")
        builder = (root / "tools/build/subtitle_runtime.py").read_text("utf8")
        self.assertNotIn("event Tick", player)
        self.assertIn("Spawn(class'LocaleSubtitleClock', Self)", player)
        self.assertIn("SubtitleClock.SubtitlePlayer = Self", player)
        self.assertIn("SubtitlePlayer.AdvanceSubtitles()", clock)
        self.assertIn("SubtitlePlayer.bDeleteMe", clock)
        self.assertIn("LocaleSubtitleClock.uc", builder)

    def test_exact_cues_and_gap(self):
        data = json.loads(
            (
                Path(__file__).resolve().parents[1] / "locales/zh-CN/subtitle-cues.json"
            ).read_text("utf8")
        )
        text = "".join(c["translation"] for c in data["cues"])
        validate_cues(data, text)
        self.assertNotIn("第一次", caption_at(data, 1.0))
        self.assertEqual(caption_at(data, 23.0), "")
        self.assertEqual(caption_at(data, 24.0), "第一次试炼，面对的是过去。")
        self.assertEqual(caption_at(data, 29.0), "坚定你的意志。")
        self.assertEqual(caption_at(data, 31.3), "")

    def test_overlap_and_changed_translation_rejected(self):
        data = {
            "cues": [
                dict(begin=0, end=2, translation="一"),
                dict(begin=1, end=3, translation="二"),
            ]
        }
        with self.assertRaises(ValueError):
            validate_cues(data, "一二")
        data["cues"][1]["begin"] = 2
        with self.assertRaises(ValueError):
            validate_cues(data, "一三")

    def test_owned_files_rollback_and_unknown_preserved(self):
        import hashlib

        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            src = root / "bundle/resources/System"
            src.mkdir(parents=True)
            for name in ["LocaleRuntime.u", "LocaleRuntime.int"]:
                (src / name).write_bytes(b"fixture")
            manifest = {
                "format": "subtitle-addon-v1",
                "files": {
                    name: {"sha256": hashlib.sha256(b"fixture").hexdigest(), "size": 7}
                    for name in ["LocaleRuntime.u", "LocaleRuntime.int"]
                },
            }
            bundle = root / "bundle/ADDON.json"
            bundle.write_text(json.dumps(manifest), "utf8")
            target = root / "target"
            manage("apply", bundle, target)
            manage("verify", bundle, target)
            manage("restore", bundle, target)
            self.assertFalse((target / "System/LocaleRuntime.u").exists())
            (target / "System/LocaleRuntime.u").write_bytes(b"other")
            with self.assertRaises(ValueError):
                manage("apply", bundle, target)
            self.assertEqual((target / "System/LocaleRuntime.u").read_bytes(), b"other")
