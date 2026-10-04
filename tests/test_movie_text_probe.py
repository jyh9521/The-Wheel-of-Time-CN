import struct
import unittest

from tools.extract.movie_text import decode_sample
from tools.pack.movie_text_probe import atoms, build, restore, sample, sha


def atom(kind, body):
    return struct.pack(">I4s", len(body) + 8, kind) + body


def fixture():
    text = b"\x00\x05Hello"
    tkhd = atom(b"tkhd", b"\x00\x00\x00\x0e" + b"\x00" * 8 + struct.pack(">I", 3))
    hdlr = atom(b"hdlr", b"\x00" * 4 + b"mhlrtext")
    def make(offset):
        stbl = atom(b"stbl", atom(b"stsd", b"\x00" * 4 + b"\x06Geneva")
                    + atom(b"stsz", struct.pack(">IIII", 0, 0, 1, len(text)))
                    + atom(b"stco", struct.pack(">III", 0, 1, offset))
                    + atom(b"stsc", struct.pack(">IIIII", 0, 1, 1, 1, 1)))
        mdhd=atom(b"mdhd",b"\x00"*24)
        return atom(b"moov", atom(b"trak", tkhd + atom(b"mdia", mdhd + hdlr + atom(b"minf", stbl))))
    moov = make(0)
    return make(len(moov) + 8) + atom(b"mdat", text)


class MovieProbeTests(unittest.TestCase):
    def setUp(self):
        self.data = fixture()
        self.config = dict(source_sha256=sha(self.data), sample_sha256=sha(sample(self.data, 3, 0)),
                           track_id=3, sample_index=0, text="新游戏，中文字幕。\r第二行",
                           source_font="Geneva", font="SimHei")

    def test_unicode_and_lossless_rollback(self):
        modified, diff = build(self.data, self.config)
        self.assertEqual(decode_sample(sample(modified, 3, 0))[0], self.config["text"])
        self.assertTrue(sample(modified, 3, 0).endswith(struct.pack(">I4sI",12,b"encd",0x100)))
        self.assertEqual(restore(modified, diff), self.data)
        media = next(a for a in atoms(self.data) if a[0] == b"mdat")
        self.assertEqual(modified[media[1]:media[1] + media[2]], self.data[media[1]:])

    def test_wrong_source(self):
        with self.assertRaisesRegex(ValueError, "Source SHA"):
            build(self.data + b"?", self.config)

    def test_wrong_sample(self):
        self.config["sample_sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "sample SHA"):
            build(self.data, self.config)

    def test_length_limit(self):
        self.config["text"] = "字" * 32767
        with self.assertRaisesRegex(ValueError, "16-bit"):
            build(self.data, self.config)

    def test_rollback_tamper(self):
        modified, diff = build(self.data, self.config)
        with self.assertRaisesRegex(ValueError, "identity"):
            restore(modified[:-1], diff)

    def test_font_size_constraint(self):
        self.config["font"] = "Different"
        with self.assertRaisesRegex(ValueError, "equal-length"):
            build(self.data, self.config)

    def test_bad_atom(self):
        with self.assertRaises(ValueError):
            list(atoms(b"\x00\x00\x00\x09mdat"))

    def test_media_language_and_rollback(self):
        self.config["media_language"]=33
        modified,diff=build(self.data,self.config)
        self.assertEqual(restore(modified,diff),self.data)
        self.assertTrue(any(e["after"]=="0021" for e in diff["edits"]))

    def test_invalid_media_language(self):
        self.config["media_language"]=-1
        with self.assertRaisesRegex(ValueError,"language"):
            build(self.data,self.config)


if __name__ == "__main__":
    unittest.main()
