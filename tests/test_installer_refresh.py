import json
from pathlib import Path
import tempfile
import unittest

from src.patch.delta import create, sha
from tools.build.refresh_installer_ui import merge_resources
from tools.validate.portable_installer_qa import config_text

ROOT = Path(__file__).resolve().parents[1]


class InstallerRefreshTests(unittest.TestCase):
    def test_config_encoding_is_detected_after_install(self):
        for encoding in ('cp1252', 'utf-16'):
            self.assertEqual(config_text('bSubtitles=True'.encode(encoding)), 'bSubtitles=True')

    def fixture(self):
        delta = create(b'original', b'old')
        entry = dict(path='System/text.int', owned=False, operations=[],
                     **{k: v for k, v in delta.items() if k not in ('operations', 'format')})
        preserved = dict(path='Movies/intro.mov', owned=False,
                         operations=[dict(payload='payload/media.bin')], modified_sha256='preserved')
        members = {'LocalizationTest/MANIFEST.json': json.dumps(dict(locale='test', files=[entry, preserved])).encode(),
                   'LocalizationTest/payload/media.bin': b'keep', 'LocalizationTest/payload/obsolete.bin': b'discard'}
        bundle = dict(locale='test', files={'System/text.int': create(b'original', b'new')})
        return members, bundle

    def test_refresh_preserves_movies_and_removes_obsolete_literals(self):
        members, bundle = self.fixture()
        with tempfile.TemporaryDirectory() as directory:
            game = Path(directory)
            (game / 'System').mkdir()
            (game / 'System/text.int').write_bytes(b'original')
            merge_resources(members, bundle, game)
        spec = json.loads(members['LocalizationTest/MANIFEST.json'])
        self.assertEqual(spec['files'][0]['modified_sha256'], sha(b'new'))
        self.assertEqual(spec['files'][1]['modified_sha256'], 'preserved')
        self.assertEqual(members['LocalizationTest/payload/media.bin'], b'keep')
        self.assertNotIn('LocalizationTest/payload/obsolete.bin', members)

    def test_locale_and_original_identity_are_required(self):
        members, bundle = self.fixture()
        bundle['locale'] = 'other'
        with self.assertRaises(ValueError):
            merge_resources(members, bundle, ROOT)
        bundle['locale'] = 'test'
        bundle['files']['System/text.int'] = create(b'wrong', b'new')
        with self.assertRaises(ValueError):
            merge_resources(members, bundle, ROOT)

    def test_path_escape_is_rejected(self):
        for path in ('../escape', 'C:/escape', '/escape', 'System\\escape'):
            members, bundle = self.fixture()
            bundle['files'] = {path: create(b'', b'new')}
            with self.assertRaises(ValueError):
                merge_resources(members, bundle, ROOT)

    def test_compact_layout_and_wrapping_footer(self):
        source = (ROOT / 'src/installer/PortableInstaller.cs').read_text('utf8')
        self.assertIn('new Size(620, 736)', source)
        self.assertIn('new Rectangle(160,8,300,150)', source)
        self.assertIn('new Rectangle(24,162,572,24)', source)
        self.assertNotIn('directoryCard.Width += 120', source)
        self.assertIn('x+width>Width', source)
        self.assertIn('InstallerLogo.png', source)

    def test_footer_is_four_paragraphs_with_locale_driven_emphasis(self):
        ui = json.loads((ROOT / 'locales/zh-CN/installer-ui.json').read_text('utf8'))
        paragraphs = ui['footnote'].split('\n\n')
        self.assertEqual(len(paragraphs), 4)
        self.assertIn('1024×768', paragraphs[2])
        self.assertIn('1920×1080', paragraphs[3])
        self.assertEqual(ui['footnote_emphasis'], '不建议')
        self.assertEqual(ui['footnote'].count(ui['footnote_emphasis']), 1)
        source = (ROOT / 'src/installer/PortableInstaller.cs').read_text('utf8')
        self.assertIn('class StyledNote : Control', source)
        self.assertIn('FontStyle.Bold', source)
        self.assertIn('Color.FromArgb(186,26,26)', source)
        self.assertNotIn('不建议', source)


if __name__ == '__main__':
    unittest.main()
