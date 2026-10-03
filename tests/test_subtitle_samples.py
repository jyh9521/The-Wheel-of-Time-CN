import unittest
from tools.validate.runtime import parse_subtitle_samples


class SubtitleSampleTests(unittest.TestCase):
    def test_extended_capture(self):
        self.assertEqual(parse_subtitle_samples("10,20,45,60,90"), (10, 20, 45, 60, 90))

    def test_invalid_order_or_range(self):
        for value in ["0", "301", "20,10", "10,10", ""]:
            with self.subTest(value=value), self.assertRaises(ValueError):
                parse_subtitle_samples(value)
