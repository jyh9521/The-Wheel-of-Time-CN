import struct
import unittest
from pathlib import Path
from types import SimpleNamespace

from tools.extract.texture_audit import decode_texture, property_end, scan
from tools.pack.ue1 import ci


class TextureAuditTests(unittest.TestCase):
    def test_nonzero_none_index(self):
        data = ci(0) + b"\x01\x07" + ci(1)
        end, tags = property_end(data, ["Format", "None"])
        self.assertEqual(end, len(data))
        self.assertEqual(tags, {0: (2, 1, 1)})

    def test_invalid_name(self):
        with self.assertRaisesRegex(ValueError, "name index"):
            property_end(ci(3), ["None"])

    def test_truncated_property(self):
        with self.assertRaisesRegex(ValueError, "payload"):
            property_end(ci(1) + b"\x21", ["None", "Width"])

    def test_p8_first_mip_versions(self):
        for version in (63, 68):
            with self.subTest(version=version):
                colors = bytes([255, 0, 0, 255, 0, 255, 0, 255]) + bytes(254 * 4)
                palette = ci(0) + ci(256) + colors
                texture = (
                    ci(1)
                    + b"\x05"
                    + ci(2)
                    + ci(0)
                    + ci(1)
                    + struct.pack("<i", 0)
                    + ci(4)
                    + bytes([0, 1, 1, 0])
                    + struct.pack("<iiBB", 2, 2, 1, 1)
                )
                pkg = SimpleNamespace(
                    ver=version,
                    names=["None", "Palette"],
                    b=texture + palette,
                    exports=[
                        {"offset": 0, "size": len(texture)},
                        {"offset": len(texture), "size": len(palette)},
                    ],
                )
                img = decode_texture(pkg, {"index": 1}, lambda _: None)
                self.assertEqual(img.size, (2, 2))
                self.assertEqual(
                    [img.getpixel((x, y)) for y in range(2) for x in range(2)],
                    [(255, 0, 0), (0, 255, 0), (0, 255, 0), (255, 0, 0)],
                )

    def test_source_output_guard(self):
        game = Path("original-fixture")
        with self.assertRaisesRegex(ValueError, "outside original"):
            scan(game, game / "audit")


if __name__ == "__main__":
    unittest.main()
