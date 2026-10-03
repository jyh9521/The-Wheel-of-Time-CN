import struct
import unittest
from src.patch.resource_fields import edit_bytes


def field():
    return dict(
        offset=2,
        type="float32-le",
        expected=0.0,
        value=24.0,
        context_offset=0,
        context_hex="abcd00000000ef",
    )


class ResourceFieldTests(unittest.TestCase):
    def test_equal_length_guarded_change(self):
        original = bytes.fromhex("abcd00000000ef")
        modified = edit_bytes(original, [field()])
        self.assertEqual(
            modified, original[:2] + struct.pack("<f", 24.0) + original[6:]
        )
        self.assertEqual(original, bytes.fromhex("abcd00000000ef"))

    def test_wrong_field_rejected(self):
        e = field()
        e["expected"] = 1.0
        with self.assertRaises(ValueError):
            edit_bytes(bytes.fromhex(e["context_hex"]), [e])

    def test_wrong_context_rejected(self):
        e = field()
        e["context_hex"] = "eeee"
        with self.assertRaises(ValueError):
            edit_bytes(bytes.fromhex("abcd00000000ef"), [e])

    def test_overlapping_fields_rejected(self):
        e = field()
        with self.assertRaises(ValueError):
            edit_bytes(bytes.fromhex(e["context_hex"]), [e, e])

    def test_invalid_offset_and_margin(self):
        for key, value in [
            ("offset", -1),
            ("offset", 4),
            ("value", float("nan")),
            ("value", -1),
            ("value", 257),
        ]:
            e = field()
            e[key] = value
            with self.assertRaises(ValueError):
                edit_bytes(bytes.fromhex(e["context_hex"]), [e])
