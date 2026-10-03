import importlib
import json
import unittest
from pathlib import Path

module = importlib.import_module("tools.import.preferences")


class PreferencesTests(unittest.TestCase):
    def test_display_only(self):
        source = '(Caption="Display",Parent="Advanced Options",Class=WinDrv.WindowsClient,Immediate=True,Category=Display)'
        rebuilt = module.replace_display(
            source, {"Caption": "显示", "Parent": "高级选项"}
        )
        fields = module.fields(rebuilt)
        self.assertEqual(fields["Caption"], "显示")
        self.assertEqual(fields["Parent"], "高级选项")
        for key in ["Class", "Immediate", "Category"]:
            self.assertEqual(fields[key], module.fields(source)[key])

    def test_machine_field_rejected(self):
        with self.assertRaisesRegex(ValueError, "Only Caption"):
            module.replace_display(
                '(Caption="Display",Category=Display)', {"Category": "显示"}
            )

    def test_control_rejected(self):
        with self.assertRaisesRegex(ValueError, "control mismatch"):
            module.replace_display(
                '(Caption="Device %s",Parent="Root")', {"Caption": "设备"}
            )

    def test_duplicate_field_rejected(self):
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            module.fields('(Caption="Audio",Caption="Display")')

    def test_unsupported_syntax_rejected(self):
        with self.assertRaisesRegex(ValueError, "Unsupported"):
            module.fields('(Caption="Display",Nested=(Key=Value))')

    def test_injected_translation_rejected(self):
        with self.assertRaisesRegex(ValueError, "Invalid display"):
            module.replace_display('(Caption="Display")', {"Caption": '显示",Class=X'})

    def test_locale_tree_connected(self):
        spec = json.loads(Path("locales/zh-CN/native-ui.json").read_text("utf8"))
        captions = {r["translations"]["Caption"] for r in spec["preferences"]}
        root = next(
            r["translation"]
            for r in spec["strings"]
            if r["file"] == "Window.int" and r["key"] == "AdvancedOptionsTitle"
        )
        self.assertTrue(
            all(
                r["translations"]["Parent"] in captions | {root}
                for r in spec["preferences"]
            )
        )
        self.assertEqual(len(spec["preferences"]), 31)

    def test_nine_top_level_categories(self):
        spec = json.loads(Path("locales/zh-CN/native-ui.json").read_text("utf8"))
        captions = {
            r["translations"]["Caption"]
            for r in spec["preferences"]
            if r["translations"]["Parent"] == "高级选项"
        }
        self.assertEqual(
            captions,
            {
                "高级",
                "音频",
                "显示",
                "驱动程序",
                "编辑器",
                "游戏设置",
                "手柄",
                "网络",
                "渲染",
            },
        )
