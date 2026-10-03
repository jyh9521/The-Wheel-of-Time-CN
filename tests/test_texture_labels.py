import unittest
from PIL import Image, ImageFont
from tools.font.build_texture_labels import raster_label


class TextureLabelTests(unittest.TestCase):
    def setUp(self):
        self.image = Image.new("RGB", (64, 64), (130, 125, 120))
        self.font = ImageFont.load_default()
        self.spec = {"rectangle": [10, 19, 54, 40], "ink_rgb": [15, 12, 9]}

    def test_only_panel_changes(self):
        result = raster_label(self.image, "Save", self.font, self.spec)
        self.assertNotEqual(result.tobytes(), self.image.tobytes())
        for y in range(64):
            for x in range(64):
                if not (10 <= x < 54 and 19 <= y < 40):
                    self.assertEqual(
                        result.getpixel((x, y)), self.image.getpixel((x, y))
                    )

    def test_deterministic(self):
        self.assertEqual(
            raster_label(self.image, "Save", self.font, self.spec).tobytes(),
            raster_label(self.image, "Save", self.font, self.spec).tobytes(),
        )

    def test_overflow_rejected(self):
        with self.assertRaisesRegex(ValueError, "fit rectangle"):
            raster_label(self.image, "X" * 100, self.font, self.spec)

    def test_empty_rejected(self):
        with self.assertRaisesRegex(ValueError, "fit rectangle"):
            raster_label(self.image, "", self.font, self.spec)

    def test_invalid_rectangle_rejected(self):
        with self.assertRaisesRegex(ValueError, "outside texture"):
            raster_label(
                self.image, "Save", self.font, dict(self.spec, rectangle=[0, 0, 64, 64])
            )
