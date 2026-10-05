import json
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

class ConfirmedMapTermsTests(unittest.TestCase):
    def test_glossary_is_authority(self):
        glossary=(ROOT/'GLOSSARY.md').read_text('utf8')
        self.assertIn('| Absynth | 阿布辛斯 |',glossary)
        self.assertIn('| Lincoln | 林肯 |',glossary)

    def test_map_display_terms_are_resolved(self):
        data=json.loads((ROOT/'locales/zh-CN/map-prompts.json').read_text('utf8'))
        rows=[r for m in data['maps'] for r in m['rows']]
        self.assertEqual(sum(r['translation']=='阿布辛斯' for r in rows),2)
        self.assertEqual(sum('林肯' in r['translation'] for r in rows),1)
        self.assertFalse(any('Absynth' in r['translation']or'Lincoln' in r['translation']for r in rows))
        self.assertFalse(any(r['term']in ('Absynth','Lincoln')for r in data['pending_terms']))
