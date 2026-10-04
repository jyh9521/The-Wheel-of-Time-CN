import copy
import json
import struct
import unittest
from pathlib import Path
from src.patch.display_expressions import digest, replace_casts
from src.patch.native_properties import reverse_values, editor_stub
from tools.validate.menu_values import scan_vm


class SettingsCompletionTests(unittest.TestCase):
    def test_arena_branch_profile(self):
        spec = json.loads(Path('profiles/gog-v68.json').read_text('utf8'))['display_expressions'][2]
        self.assertEqual(spec['export'], 'menuStartArenaServer.UpdateValues')
        self.assertEqual(spec['helper'], 'GetOnOffStr')
        self.assertEqual(spec['script_size'], 406)
        self.assertEqual([e['menu_slot'] for e in spec['edits']], [4])
        self.assertEqual(len(spec['jumps']), 2)

    def test_synthetic_branch_after_cast_relocated(self):
        header = b'\0' * 6 + struct.pack('<iii', 1, 2, 13)
        original = header + bytes.fromhex('060b0004542d0101040b') + b'\0' * 7
        spec = dict(export_sha256=digest(original), script_size=13,
                    jumps=[dict(offset=19, target=11)],
                    edits=[dict(offset=22, argument_hex='2d0101', menu_slot=4, vm_start=4)])
        modified = replace_casts(original, spec, 400)
        size, jumps, boundaries = scan_vm(modified)
        self.assertEqual(size, 18)
        self.assertEqual(jumps, [(19, 16)])
        self.assertIn(16, boundaries)
        bad = copy.deepcopy(spec)
        bad['jumps'][0]['target'] = 10
        with self.assertRaises(ValueError):
            replace_casts(original, bad, 400)

    def test_reverse_display_values(self):
        values = json.loads(Path('locales/zh-CN/native-properties.json').read_text('utf8'))['values']
        inverse = reverse_values(values)
        self.assertEqual(inverse['开'], 'True')
        self.assertEqual(inverse['关'], 'False')
        for raw, display in values.items():
            self.assertEqual(inverse[display], raw)
        with self.assertRaises(ValueError):
            reverse_values({'True':'开', 'False':'开'})
        with self.assertRaises(ValueError):
            reverse_values({'True':'True'})

    def test_editor_stubs_rebase_and_unknown_guard(self):
        for kind in ['combo_add', 'combo_find', 'combo_save']:
            self.assertEqual(editor_stub(kind, 0x11064000, 0x11065000, 0x110199bd),
                             editor_stub(kind, 0x21064000, 0x21065000, 0x210199bd))
        with self.assertRaises(ValueError):
            editor_stub('shared_setter', 0, 0, 0)
        sites = json.loads(Path('profiles/gog-v68.json').read_text('utf8'))['native_properties']['editor_sites']
        self.assertEqual([s['kind'] for s in sites].count('combo_add'), 6)
        self.assertEqual([s['kind'] for s in sites].count('combo_find'), 1)
        self.assertEqual([s['kind'] for s in sites].count('combo_save'), 1)
