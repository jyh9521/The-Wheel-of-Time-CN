import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from fontTools.fontBuilder import FontBuilder
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.ttLib import TTFont
from tools.font.build_subset import build, sha
from src.patch.local_font_loader import assemble, patch


class FontSubsetTests(unittest.TestCase):
    def fixture(self, folder):
        source=folder/'input.ttf';fb=FontBuilder(1000,isTTF=True)
        chars=set(range(32,127))|set(map(ord,'里斯琳'))
        mapping={c:'u%04X'%c for c in chars};order=['.notdef']+list(mapping.values())
        fb.setupGlyphOrder(order);fb.setupCharacterMap(mapping)
        glyphs={}
        for name in order:
            pen=TTGlyphPen(None);pen.moveTo((100,0));pen.lineTo((600,0));pen.lineTo((600,700));pen.lineTo((100,700));pen.closePath();glyphs[name]=pen.glyph()
        fb.setupGlyf(glyphs);fb.setupHorizontalMetrics({n:(1000,0)for n in order})
        fb.setupHorizontalHeader(ascent=800,descent=-200)
        fb.setupNameTable(dict(familyName='Original',styleName='Regular',uniqueFontIdentifier='Original-1',fullName='Original',psName='Original-Regular',version='Version 1.0',copyright='Test font copyright'))
        fb.setupOS2(sTypoAscender=800,sTypoDescender=-200,usWinAscent=800,usWinDescent=200,ulCodePageRange1=0x40001)
        fb.setupPost();fb.save(source)
        translations=folder/'locale';translations.mkdir();(translations/'Movie.tsv').write_text('1\t里斯琳 abc\n','utf8')
        license_path=folder/'license.txt';license_path.write_text('Test license fixture','utf8')
        return source,translations,license_path

    def test_reproducible_renamed_subset_and_script_mask(self):
        with tempfile.TemporaryDirectory() as name:
            root=Path(name);source,texts,license_path=self.fixture(root);before=source.read_bytes()
            with contextlib.redirect_stdout(io.StringIO()):
                a=build(source,texts,root/'a/font.ttf','WotFmv',license_path,code_page_mask=0x40001)
                b=build(source,texts,root/'b/font.ttf','WotFmv',license_path,code_page_mask=0x40001)
            self.assertEqual(a,b);self.assertEqual(source.read_bytes(),before)
            f=TTFont(root/'a/font.ttf')
            self.assertEqual(f['OS/2'].ulCodePageRange1,0x40001)
            self.assertEqual(f['name'].getDebugName(1),'WotFmv')
            self.assertEqual(f['name'].getDebugName(0),'Test font copyright')
            self.assertTrue(set(map(ord,'里斯琳'))<=set(f.getBestCmap()))
            self.assertEqual((root/'a/OFL.txt').read_bytes(),license_path.read_bytes())

    def test_missing_glyph_fails_without_output(self):
        with tempfile.TemporaryDirectory() as name:
            root=Path(name);source,texts,license_path=self.fixture(root)
            (texts/'Movie.tsv').write_text('1\t缺\n','utf8')
            with self.assertRaisesRegex(ValueError,'Missing glyphs'):
                build(source,texts,root/'out/font.ttf','WotFmv',license_path)
            self.assertFalse((root/'out/font.ttf').exists())

    def test_unknown_dll_and_font_escape_rejected(self):
        for rel in ['../font.ttf','/font.ttf','C:/font.ttf','Fonts/file.otf']:
            with self.assertRaises(ValueError):patch(b'',{},rel)
        with self.assertRaises(ValueError):patch(b'unknown',dict(size=0,sha256=''), 'Fonts/font.ttf')

    def test_runtime_config_exception_is_explicit_and_narrow(self):
        from tools.build.build_local_font_poc import verify_file_identity
        with tempfile.TemporaryDirectory() as name:
            root=Path(name);(root/'System').mkdir()
            files=['System/WoT.ini','System/User.ini','System/WinDrv.dll']
            for file in files:(root/file).write_bytes(b'original')
            manifest=dict(files=[dict(file=f,source_sha256=sha(b'original')) for f in files],modified={})
            (root/files[0]).write_bytes(b'1920x1080')
            with self.assertRaisesRegex(ValueError,'WoT.ini'):verify_file_identity(root,manifest)
            self.assertEqual(verify_file_identity(root,manifest,True),[files[0]])
            (root/files[2]).write_bytes(b'bad')
            with self.assertRaisesRegex(ValueError,'WinDrv.dll'):verify_file_identity(root,manifest,True)
            (root/files[2]).write_bytes(b'original');manifest['modified'][files[0]]=sha(b'original')
            with self.assertRaisesRegex(ValueError,'WoT.ini'):verify_file_identity(root,manifest,True)

    def test_adapter_has_pic_preamble_and_no_writable_code_requirement(self):
        code,asm=assemble(0x50000,0x51000,0x17e50,
                         dict(GetModuleHandleA=0x42dac,GetProcAddress=0x42dbc,LoadLibraryA=0x42dc0),
                         dict(kernel=0x50400,filename_api=0x50420,gdi=0x50440,font_api=0x50460,suffix=0x50480,suffix_chars=20))
        self.assertEqual(code[:7],bytes.fromhex('9c60e800000000'))
        self.assertLess(len(code),0x400)
        self.assertIn('push 0x10',asm)
        self.assertIn('popfd',asm)


if __name__=='__main__':unittest.main()
