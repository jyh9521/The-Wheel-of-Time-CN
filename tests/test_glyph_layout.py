import unittest
from PIL import ImageFont
from tools.font.raster import layout, render


class BoundsFont:
    def getbbox(self, ch):
        return {
            "anchor": (0, 4, 14, 17),
            "tall": (-1, 2, 14, 16),
            "period": (0, 14, 14, 17),
        }[ch]


class GlyphLayoutTests(unittest.TestCase):
    def test_taller_glyph_not_clipped_by_anchor(self):
        m = layout(BoundsFont(), ["anchor", "tall", "period"], 14)
        self.assertEqual(m["source_bounds"], [-1, 2, 14, 17])
        self.assertEqual(m["origin"], [1, -1])
        self.assertEqual(m["height"], 17)
        self.assertEqual(m["base_width"], 15)

    def test_period_bearing_not_top_aligned(self):
        m = layout(BoundsFont(), ["anchor", "tall", "period"], 14)
        self.assertEqual(14 + m["origin"][1], 13)

    def test_configurable_padding(self):
        m = layout(
            BoundsFont(), ["anchor", "tall"], 14, top_padding=3, bottom_padding=2
        )
        self.assertEqual(m["origin"], [1, 1])
        self.assertEqual(m["height"], 20)

    def test_oblique_reserves_full_cell_width(self):
        m = layout(BoundsFont(), ["tall"], 14, skew=0.22)
        self.assertGreater(m["width"], m["base_width"])

    def test_invalid_padding_rejected(self):
        for padding in [-1, 33, True, 1.5]:
            with self.assertRaises(ValueError):
                layout(BoundsFont(), ["tall"], 14, top_padding=padding)

    def test_actual_raster_keeps_reference_ink(self):
        f = ImageFont.load_default(size=14)
        m = layout(f, "Agj.", 14)
        for ch in "Agj.":
            self.assertIsNotNone(render(f, ch, m).getbbox())

    def test_undersized_cell_rejected(self):
        f = ImageFont.load_default(size=14)
        m = layout(f, "Agj.", 14)
        m["raster_height"] = 1
        with self.assertRaises(ValueError):
            render(f, "A", m)

    def test_preserve_legacy_height_without_cropping_source(self):
        m = layout(
            BoundsFont(),
            ["anchor", "tall", "period"],
            14,
            top_padding=0,
            bottom_padding=0,
            fit_height=14,
        )
        self.assertEqual(m["height"], 14)
        self.assertEqual(m["raster_height"], 15)
        self.assertEqual(m["source_bounds"], [-1, 2, 14, 17])

    def test_fitted_raster_retains_nonempty_glyphs(self):
        f = ImageFont.load_default(size=14)
        m = layout(f, "Agj.", 14, top_padding=0, bottom_padding=0, fit_height=14)
        for ch in "Agj.":
            mask = render(f, ch, m)
            self.assertEqual(mask.height, 14)
            self.assertIsNotNone(mask.getbbox())
