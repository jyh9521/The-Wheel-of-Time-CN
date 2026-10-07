import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
import zipfile

from src.patch.delta import create
from tools.build.package_player_test import package


class PlayerPackageTests(unittest.TestCase):
    def fixture(self, root):
        game, build, runtime = (root / name for name in ("game", "build", "runtime"))
        for folder in (game / "System", game / "Movies", build, runtime / "System", runtime / "Movies", runtime / "Fonts"):
            folder.mkdir(parents=True)
        original = b"old menu"
        modified = b"localized menu"
        (game / "System/Sample.int").write_bytes(original)
        (runtime / "System/Sample.int").write_bytes(modified)
        (game / "System/WoT.exe").write_bytes(b"original executable must not be packaged")
        (game / "System/WinDrv.dll").write_bytes(b"original driver")
        (runtime / "System/WinDrv.dll").write_bytes(b"original driver plus font loader")
        media = b"original movie stream" * 7000
        (game / "Movies/Intro.mov").write_bytes(media)
        (runtime / "Movies/Intro.mov").write_bytes(media[:2] + b"XX" + media[4:] + b"translated captions")
        for name in ("WotFmv.ttf", "OFL.txt"):
            (runtime / "Fonts" / name).write_bytes(b"owned font or license")
        (build / "PATCH.json").write_text(json.dumps({"locale": "zh-CN", "files": {"System/Sample.int": create(original, modified)}, "owned_additions": []}))
        return game, build, runtime

    def test_standalone_reproducible_delta_only_package(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            game, build, runtime=self.fixture(root)
            with contextlib.redirect_stdout(io.StringIO()):
                manifest=package(game, build, runtime, root / "first.zip")
                package(game, build, runtime, root / "second.zip")
            self.assertEqual((root / "first.zip").read_bytes(), (root / "second.zip").read_bytes())
            with zipfile.ZipFile(root / "first.zip") as archive:
                self.assertIsNone(archive.testzip())
                self.assertFalse(any(n.startswith(("System/", "Movies/", "Maps/")) for n in archive.namelist()))
                self.assertNotIn(b"original executable must not be packaged", archive.read("LocalizationTest/MANIFEST.json"))
                self.assertNotIn(b"python", archive.read("Install-Localization.cmd"))
                for entry in manifest["files"]:
                    original=b"" if entry["owned"] else (game / entry["path"]).read_bytes()
                    output=bytearray()
                    for op in entry["operations"]:
                        output.extend(original[op["copy"]:op["copy"]+op["size"]] if "copy" in op else archive.read("LocalizationTest/"+op["payload"]))
                    self.assertEqual(bytes(output), (runtime / entry["path"]).read_bytes())

    def test_stale_runtime_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);game,build,runtime=self.fixture(root)
            (runtime / "System/Sample.int").write_bytes(b"stale")
            with self.assertRaisesRegex(ValueError,"runtime differs"):
                package(game, build, runtime, root / "bad.zip")
            self.assertFalse((root / "bad.zip").exists())

    def test_unknown_original_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);game,build,runtime=self.fixture(root)
            (game / "System/Sample.int").write_bytes(b"unknown version")
            with self.assertRaisesRegex(ValueError,"fingerprint"):
                package(game, build, runtime, root / "bad.zip")


if __name__ == "__main__":
    unittest.main()
