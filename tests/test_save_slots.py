import json
from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[1]
class SaveSlotTests(unittest.TestCase):
 def test_slot_names_have_locale_data_and_match_guard(self):
  data=json.loads((ROOT/'locales/zh-CN/save-slots.json').read_text('utf8'))
  rows=json.loads((ROOT/'locales/zh-CN/strings.json').read_text('utf8'))
  empty=next(r['translation'] for r in rows if r['section']=='menuSlot' and r['key']=='EmptySlotName')
  self.assertEqual(data['translation'],empty)
  self.assertEqual(data['keys'],['SlotNames[%d]'%i for i in range(9)])
  self.assertEqual(data['match_values'],['..Empty..'])
  backend=(ROOT/'assets/templates/player-test.ps1').read_text('utf8')
  self.assertIn('-notin $change.match_values',backend)
  self.assertIn('$enc.GetString($enc.GetBytes($text)) -ne $text',backend)
  self.assertIn("slots['match_values']",(ROOT/'tools/build/package_player_test.py').read_text('utf8'))
