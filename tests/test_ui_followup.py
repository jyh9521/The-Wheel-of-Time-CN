import json
import unittest
from pathlib import Path
from tools.extract.movie_text import decode_sample
from src.patch.key_display import rewrite

ROOT = Path(__file__).resolve().parents[1]


class UIFollowupTests(unittest.TestCase):
    def test_keys_cover_profile_and_standard_caps(self):
        spec = json.loads((ROOT / "profiles/gog-v68.json").read_text("utf8"))[
            "key_display"
        ]
        labels = json.loads((ROOT / "locales/zh-CN/key-names.json").read_text("utf8"))
        self.assertEqual(set(labels), set(spec["keys"]) | {"_"})
        self.assertEqual(labels["LeftMouse"], "鼠标左键")
        self.assertEqual(labels["RightBracket"], "右方括号键")
        self.assertEqual(labels["F2"], "F2")
        self.assertNotEqual(labels["Shift"], "瞬移")

    def test_unknown_export_rejected(self):
        with self.assertRaisesRegex(ValueError, "fingerprint"):
            rewrite(b"unknown", {"export_sha256": "0" * 64}, 1)

    def test_movie_samples(self):
        self.assertEqual(decode_sample(b"\0\x03abc\0\0")[0], "abc")
        self.assertEqual(decode_sample(b"\0\0")[0], "")
        text = b"\xfe\xff" + "中文".encode("utf-16be")
        self.assertEqual(decode_sample(len(text).to_bytes(2, "big") + text)[0], "中文")
        for data in [b"", b"\0\x04abc"]:
            with self.assertRaises(ValueError):
                decode_sample(data)

    def test_prompt_coverage_and_control_prefix(self):
        data = json.loads(
            (ROOT / "locales/zh-CN/tutorial-prompts.json").read_text("utf8")
        )
        self.assertEqual(len(data["rows"]), 35)
        self.assertEqual(len({(r["actor"], r["slot"]) for r in data["rows"]}), 35)
        self.assertTrue(
            next(r for r in data["rows"] if r["actor"] == "MessageTrigger1")[
                "translation"
            ].startswith(" //")
        )

    def test_quote_punctuation_preserved_and_shortened(self):
        rows = json.loads((ROOT / "locales/zh-CN/strings.json").read_text("utf8"))
        quote = next(
            r["translation"]
            for r in rows
            if r["file"] == "Angreal.int"
            and r["section"] == "AngrealInvAirBurst"
            and r["key"] == "Quote"
        )
        self.assertEqual(quote, "他仿佛被巨手击中，飞出十步，重重撞上石头。")


if __name__ == "__main__":
    unittest.main()
