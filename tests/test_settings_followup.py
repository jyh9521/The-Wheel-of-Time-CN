import json
import struct
import unittest
from pathlib import Path
from src.patch.credits import read_rows, write_rows
from src.patch.display_expressions import digest, replace_casts, script_header
from src.patch.native_properties import lookup
from install import targets


class SettingsFollowupTests(unittest.TestCase):
    def test_credits_unicode_array_roundtrip(self):
        rows = [(i, '译文：伯翎飞云 - Name' if i % 3 else ' ')
                for i in range(206)]
        raw = write_rows(rows, 18)
        self.assertEqual(read_rows(raw, 0, 18), rows)

    def test_credits_long_payload_and_zero_protected(self):
        rows = [(0, '文字' * 100)]
        self.assertEqual(read_rows(write_rows(rows, 18), 0, 18), rows)
        with self.assertRaises(ValueError):
            write_rows([(0, 'a\0b')], 18)

    def test_attribution_appended_without_replacing_original_rows(self):
        data = json.loads(Path('locales/zh-CN/credits.json').read_text('utf8'))
        self.assertEqual([r['slot'] for r in data['rows']], list(range(206)))
        self.assertTrue(all('source_sha256' in r for r in data['rows'][:204]))
        self.assertEqual(data['rows'][-1]['translation'], '简体中文补丁制作：伯翎飞云')

    def test_credits_sitter_uses_existing_sole_glossary(self):
        from tools.validate.terminology import load_terms
        terms = dict(load_terms(Path('GLOSSARY.md'), '中文译名'))
        data = json.loads(Path('locales/zh-CN/credits.json').read_text('utf8'))
        self.assertIn(terms['Sitter'], data['rows'][110]['translation'])
        self.assertNotIn('Sitter', data['pending_terms'])

    def test_confirmed_credits_character_names(self):
        from tools.validate.terminology import load_terms
        terms = dict(load_terms(Path('GLOSSARY.md'), '中文译名'))
        data = json.loads(Path('locales/zh-CN/credits.json').read_text('utf8'))
        self.assertEqual(terms['Poleine'], '波莱恩')
        self.assertEqual(terms['Kyrin'], '凯琳')
        self.assertEqual(data['rows'][107]['translation'], terms['Poleine'] + ' - Carolyn Stewart')
        self.assertEqual(data['rows'][118]['translation'], terms['Kyrin'] + ' - Kathleen Bober')
        self.assertEqual(data['pending_terms'], [])

    def test_texture_detail_vm_delta(self):
        profile = json.loads(Path('profiles/gog-v68.json').read_text('utf8'))
        spec = profile['display_expressions'][1]
        self.assertEqual(spec['export'], 'menuConfiguration.GetTextureDetailLevelStr')
        self.assertEqual(spec['edits'][0]['vm_delta'], 40)
        expression = bytes.fromhex(spec['edits'][0]['replacement_hex'])
        self.assertIn(b'Medium\0', expression)
        self.assertIn(b'High\0', expression)
        self.assertNotIn('高'.encode('utf-16le'), expression)
        # Low=0, Medium=1, High=2, matching existing locale-neutral helper.
        self.assertEqual([int(v == 'Medium') + 2 * int(v == 'High')
                          for v in ('Low', 'Medium', 'High')], [0, 1, 2])

    def test_lookup_rejects_embedded_null(self):
        with self.assertRaises(ValueError):
            lookup({'Field':'字\0段'}, 0x11064000)

    def test_lookup_position_independent_bytes(self):
        mapping = {'Field':'字段'}
        self.assertEqual(lookup(mapping, 0x11064000), lookup(mapping, 0x21064000))

    def test_native_display_values_not_config_assignments(self):
        config = json.loads(Path('locales/zh-CN/native-properties.json').read_text('utf8'))
        self.assertEqual(config['values']['True'], '开')
        self.assertEqual(config['values']['False'], '关')
        self.assertEqual(config['labels']['TextureDetail'], '纹理细节')
        self.assertEqual(config['row_height'], 32)
        self.assertEqual(config['minimum_divider_width'], 320)

    def test_only_profiled_native_display_dll_allowed(self):
        profile = json.loads(Path('profiles/gog-v68.json').read_text('utf8'))
        original = profile['files']['System/Window.dll']
        delta = dict(original_sha256=original['sha256'], original_size=original['size'])
        bundle = dict(format='localization-bundle-v1', profile=profile['id'], files={'System/Window.dll':delta})
        self.assertIn('System/Window.dll', targets(Path.cwd(), bundle))
        bundle['profile'] = 'unknown'
        with self.assertRaises(ValueError):
            targets(Path.cwd(), bundle)
        for name in ('System/Engine.dll', 'System/WoT.exe'):
            bundle['files'] = {name:delta}
            with self.assertRaises(ValueError):
                targets(Path.cwd(), bundle)
