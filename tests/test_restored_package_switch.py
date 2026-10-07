import unittest
from pathlib import Path

class RestoredPackageSwitchTests(unittest.TestCase):
    def test_restored_state_requires_original_resources(self):
        source=(Path(__file__).resolve().parents[1]/'assets/templates/player-test.ps1').read_text('utf8')
        block=source.split('# A completed restore',1)[1].split("if ($Action -eq 'check')",1)[0]
        self.assertIn("$Action -eq 'check' -or $Action -eq 'apply'",block)
        self.assertIn('Test-Path (Target $e.path)',block)
        self.assertIn('$e.original_sha256 $e.original_size',block)
        self.assertIn("if(!$restored)",block)

if __name__=='__main__':unittest.main()
