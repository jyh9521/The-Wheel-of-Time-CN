import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from tools.build.package_preview import package
from src.patch.delta import create


class PreviewPackageTests(unittest.TestCase):
    def setup_build(self, root):
        build = root / "build"
        (build / "resources/System").mkdir(parents=True)
        delta = create(b"Old", b"New")
        (build / "resources/System/Sample.int").write_bytes(b"New")
        (build / "PATCH.json").write_text(
            json.dumps(dict(files={"System/Sample.int": delta}))
        )
        (build / "BUILD_REPORT.json").write_text(
            json.dumps(
                dict(
                    files={
                        "System/Sample.int": dict(
                            modified_sha256=delta["modified_sha256"]
                        )
                    }
                )
            )
        )
        notes = root / "QA.md"
        notes.write_text("Test notes")
        return build, notes

    def test_self_contained_package_excludes_complete_resources(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            build, notes = self.setup_build(root)
            output = package(build, root / "preview.zip", notes)
            with zipfile.ZipFile(output) as archive:
                self.assertIn("src/patch/delta.py", archive.namelist())
                self.assertIn("Manage-Patch.ps1", archive.namelist())
                self.assertNotIn("resources/System/Sample.int", archive.namelist())
                self.assertIsNone(archive.testzip())

    def test_wrong_generated_resource_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            build, notes = self.setup_build(root)
            (build / "resources/System/Sample.int").write_bytes(b"Wrong")
            with self.assertRaisesRegex(ValueError, "fingerprint"):
                package(build, root / "preview.zip", notes)
            self.assertFalse((root / "preview.zip").exists())
