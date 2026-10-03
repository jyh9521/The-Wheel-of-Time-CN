import tempfile
import unittest
from pathlib import Path

from tools.migration.inventory import compare, run, snapshot


class MigrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / "data.txt").write_bytes(b"original")

    def test_read_only(self):
        before = snapshot(self.root)
        self.assertEqual(before, snapshot(self.root))
        self.assertEqual(len(list(self.root.iterdir())), 1)

    def test_output_inside_root_rejected(self):
        with self.assertRaisesRegex(ValueError, "outside"):
            run(self.root, self.root / "audit.json")
        self.assertFalse((self.root / "audit.json").exists())

    def test_changes_detected(self):
        before = snapshot(self.root)
        (self.root / "data.txt").write_bytes(b"modified")
        (self.root / "added.txt").write_bytes(b"new")
        delta = compare(before, snapshot(self.root))
        self.assertEqual(delta["changed"], ["data.txt"])
        self.assertEqual(delta["added"], ["added.txt"])
        (self.root / "data.txt").unlink()
        self.assertEqual(compare(before, snapshot(self.root))["removed"], ["data.txt"])

    def test_duplicate_inventory_rejected(self):
        rows = snapshot(self.root)
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            compare(rows + rows, rows)
