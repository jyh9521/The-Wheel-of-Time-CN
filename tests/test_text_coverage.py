import hashlib
import tempfile
import unittest
from pathlib import Path
from tools.validate.text_coverage import audit


class TextCoverageTests(unittest.TestCase):
    def test_nonempty_not_equivalent_to_translation(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "sample.int").write_text(
                '[A]\nName="Unconfirmed"\nText="Missing"\nCode="%f=2"\nEmpty=""\n',
                "utf8",
            )
            base = dict(file="sample.int", section="A", occurrence=1)
            rows = [
                base
                | dict(
                    key="Name",
                    translation="Unconfirmed",
                    source_sha256=hashlib.sha256(b"Unconfirmed").hexdigest(),
                )
            ]
            kept = base | dict(
                key="Code",
                reason="format-control",
                source_sha256=hashlib.sha256(b"%f=2").hexdigest(),
            )
            policy = dict(files=["sample.int"], preserved_entries=[kept])
            result = audit(rows, root, policy)
            self.assertEqual(result["populated"], 1)
            self.assertEqual(result["preserved"], 1)
            self.assertEqual(len(result["missing"]), 1)
            self.assertEqual(len(result["source_equal"]), 1)
            self.assertFalse(result["semantic_review_complete"])
            kept["source_sha256"] = "0" * 64
            with self.assertRaises(ValueError):
                audit(rows, root, policy)
