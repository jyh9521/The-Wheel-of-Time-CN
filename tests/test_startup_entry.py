"""Full-game launchers must retain the stock no-map startup path."""
import unittest
from pathlib import Path
class StartupEntryTests(unittest.TestCase):
 def test_full_game_templates_use_stock_startup(self):
  root=Path(__file__).resolve().parents[1]
  for name in ['build_fmv.py','build_fmv_game_probe.py','build_local_font_poc.py']:
   with self.subTest(tool=name):
    text=(root/'tools/build'/name).read_text(encoding='utf8')
    self.assertNotIn('WoT.exe Entry',text)
    self.assertIn('WoT.exe } finally { Pop-Location }',text)
