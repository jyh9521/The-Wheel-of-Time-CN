from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class ProgressPreservationTests(unittest.TestCase):
    def test_restore_never_replaces_current_configuration(self):
        source = (ROOT / 'assets/templates/player-test.ps1').read_text('utf8')
        block = source.split("if ($Action -eq 'restore')", 1)[1].split("if (Test-Path $statePath)", 1)[0]
        self.assertNotIn('foreach($c in $state.config)', block)
        self.assertIn("Snapshot-Progress 'restore'", block)
        self.assertIn('current settings and save slots preserved', block)
        self.assertLess(block.index("Snapshot-Progress 'restore'"), block.index('foreach($e in $m.files) {$p=Target'))

    def test_snapshot_includes_current_configuration_and_save_files(self):
        source = (ROOT / 'assets/templates/player-test.ps1').read_text('utf8')
        block = source.split('function Snapshot-Progress', 1)[1].split('function Edit-Ini', 1)[0]
        for marker in ('$m.config', '$m.progress.directories', 'Get-ChildItem -LiteralPath $folder -File',
                       'SNAPSHOT.json', 'Progress snapshot differs', 'ReparsePoint', 'Progress path escape'):
            self.assertIn(marker, block)
        self.assertNotIn('[IO.File]::Delete', block)
        self.assertIn("Snapshot-Progress 'apply'", source)

    def test_prior_manifest_recovery_is_explicit_and_hash_gated(self):
        source = (ROOT / 'assets/templates/player-test.ps1').read_text('utf8')
        self.assertIn("$Action -eq 'restore' -and", source)
        self.assertIn('RESTORE_MANIFESTS.json', source)
        self.assertIn('$known.PSObject.Properties[$existing.manifest_sha256]', source)
        self.assertIn('matching recovery manifest required', source)
        self.assertIn('$e.modified_sha256 $e.modified_size', source)


if __name__ == '__main__':
    unittest.main()
