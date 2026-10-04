import copy
import json
import struct
import unittest
from pathlib import Path
from src.patch.display_expressions import digest, replace_casts, script_header
from tools.pack.ue1 import ci


def fixture():
    # Synthetic function, not bytes copied from proprietary game code.
    header = b'\0' * 6 + struct.pack('<iii', 1, 2, 10)
    raw = header + bytes.fromhex('04542d0101040b') + b'\0' * 7
    spec = dict(export_sha256=digest(raw), script_size=10,
                edits=[dict(offset=len(header) + 1, argument_hex='2d0101', menu_slot=2)])
    return raw, spec


class DisplayExpressionTests(unittest.TestCase):
    def test_same_bool_operand_existing_helper(self):
        raw, spec = fixture()
        for index in (5, 400):
            modified = replace_casts(raw, spec, index)
            _, start, size = script_header(modified)
            self.assertEqual(size, 15)
            self.assertEqual(modified[start:-7], b'\x04\x1b' + ci(index) + bytes.fromhex('2d010116040b'))
            self.assertEqual(modified[-7:], raw[-7:])

    def test_unknown_function_rejected(self):
        raw, spec = fixture()
        with self.assertRaisesRegex(ValueError, 'fingerprint'):
            replace_casts(raw + b'\0', spec, 400)

    def test_repeat_apply_rejected(self):
        raw, spec = fixture()
        with self.assertRaisesRegex(ValueError, 'fingerprint'):
            replace_casts(replace_casts(raw, spec, 400), spec, 400)

    def test_size_expected_pattern_and_overlap_guards(self):
        raw, original = fixture()
        for edit in ('size', 'argument', 'overlap', 'bounds'):
            spec = copy.deepcopy(original)
            if edit == 'size':
                spec['script_size'] = 11
            elif edit == 'argument':
                spec['edits'][0]['argument_hex'] = '2d0102'
            elif edit == 'overlap':
                spec['edits'] *= 2
            else:
                spec['edits'][0]['offset'] = 1
            with self.subTest(edit=edit), self.assertRaises(ValueError):
                replace_casts(raw, spec, 400)

    def test_profile_scoped_to_six_controls(self):
        profile = json.loads(Path('profiles/gog-v68.json').read_text('utf8'))
        specs = profile['display_expressions']
        self.assertEqual(len(specs), 3)
        self.assertEqual(specs[0]['export'], 'menuOptions.DrawValues')
        self.assertEqual(specs[0]['helper'], 'GetOnOffStr')
        self.assertEqual([e['menu_slot'] for e in specs[0]['edits']], [2, 4, 5, 6, 9, 11])

    def test_locale_labels_exist(self):
        rows = json.loads(Path('locales/zh-CN/strings.json').read_text('utf8'))
        labels = {r['key']: r['translation'] for r in rows
                  if r['file'] == 'WoT.int' and r['section'] == 'menuLong'}
        self.assertEqual(labels['OnText'], '开')
        self.assertEqual(labels['OffText'], '关')
