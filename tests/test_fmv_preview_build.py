import json
import tempfile
import unittest
from pathlib import Path

from tools.build.build_fmv_preview import write_owned


class PreviewBuildTests(unittest.TestCase):
    def test_existing_identical_movie_is_reused(self):
        with tempfile.TemporaryDirectory() as directory:
            p=Path(directory)/"probe.mov"
            write_owned(p,b"owned")
            write_owned(p,b"owned")
            self.assertEqual(p.read_bytes(),b"owned")

    def test_unknown_output_is_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            p=Path(directory)/"probe.mov"
            p.write_bytes(b"unknown")
            with self.assertRaisesRegex(ValueError,"Existing output differs"):
                write_owned(p,b"owned")
            self.assertEqual(p.read_bytes(),b"unknown")

    def test_crlf_json_is_semantically_reused(self):
        with tempfile.TemporaryDirectory() as directory:
            p=Path(directory)/"probe.json"
            data=json.dumps({"offset":12},indent=2).encode()
            p.write_bytes(data.replace(b"\n",b"\r\n"))
            write_owned(p,data)
            self.assertIn(b"\r\n",p.read_bytes())

    def test_different_manifest_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            p=Path(directory)/"probe.json"
            p.write_text('{"offset":13}',encoding="utf8")
            with self.assertRaises(ValueError):
                write_owned(p,b'{"offset":12}')


if __name__=="__main__":
    unittest.main()
