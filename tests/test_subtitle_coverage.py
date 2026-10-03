import unittest
from tools.validate.subtitle_coverage import correlate, index


class SubtitleCoverageTests(unittest.TestCase):
    def test_states_and_static_associations(self):
        rows = [
            dict(section="DialogA", key="Tes_01", source="Hello", empty=False),
            dict(section="DialogA", key="Tes_02", source="", empty=True),
        ]
        sounds = [
            dict(sound="DialogA." + name, section="DialogA", key=name)
            for name in ["Tes_01", "Tes_02", "Tes_03"]
        ]
        result = correlate(
            rows,
            sounds,
            {"Tutorial.wot": ["dialoga.tes_01"]},
            [
                dict(
                    file="WoTsubtitles.int",
                    section="DialogA",
                    key="Tes_01",
                    translation="你好",
                )
            ],
        )
        self.assertEqual(result["counts"], {"text": 1, "empty": 1, "missing-key": 1})
        self.assertEqual(result["sounds"][0]["maps"], ["Tutorial.wot"])
        self.assertEqual(result["sounds"][0]["translation_state"], "translated")
        self.assertFalse(result["sounds"][0]["runtime_verified"])

    def test_duplicate_case_insensitive_rejected(self):
        with self.assertRaises(ValueError):
            index([dict(section="A", key="B"), dict(section="a", key="b")])

    def test_orphan_is_not_discarded(self):
        result = correlate(
            [dict(section="A", key="B", source="x", empty=False)], [], {}, []
        )
        self.assertEqual(result["orphan_subtitle_keys"], [dict(section="A", key="B")])

    def test_non_subtitle_translations_are_ignored(self):
        result = correlate(
            [],
            [dict(sound="A.B", section="A", key="B")],
            {},
            [dict(file="WoT.int", section="A", key="B", translation="x")],
        )
        self.assertEqual(result["sounds"][0]["translation_state"], "pending")
