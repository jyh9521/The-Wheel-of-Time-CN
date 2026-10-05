import copy
import struct
import tempfile
import unittest
from pathlib import Path
from src.patch.map_prompts import build, restore, sha
from tools.extract.map_messages import entries
from tools.pack.ue1 import ci, Package, body


def fixture(path):
    names = ['None', 'Messages', 'MessageTrigger', 'Hint', 'Other']
    data = bytearray(128)
    name_offset = len(data)
    for name in names:
        text = name.encode() + b'\0'
        data += ci(len(text)) + text + struct.pack('<i', 0)
    import_offset = len(data)
    data += ci(0) + ci(0) + struct.pack('<i', 0) + ci(2)
    payload = ci(9) + b'Press %s\0'
    # Include an array index and a non-property actor trailer.
    actor = ci(0) + ci(0) + bytes(12) + ci(1) + b'\xfd' + struct.pack('<i', len(payload)) + b'\x02' + payload + ci(0) + b'ACTOR_TRAILER'
    actor_offset = len(data)
    data += actor
    other_offset = len(data)
    data += b'unchanged export'
    export_offset = len(data)
    data += ci(-1) + ci(0) + struct.pack('<i', 0) + ci(3) + struct.pack('<I', 0x02000000) + ci(len(actor)) + ci(actor_offset)
    data += ci(0) + ci(0) + struct.pack('<i', 0) + ci(4) + struct.pack('<I', 0) + ci(16) + ci(other_offset)
    struct.pack_into('<IHHIiiiiii', data, 0, 0x9E2A83C1, 68, 0, 0, len(names), name_offset, 2, export_offset, 1, import_offset)
    path.write_bytes(data)
    return dict(sha256=sha(data), rows=[dict(actor='Hint', slot=2, source_sha256=sha(b'Press %s'), translation='按 %s')])


class MapPromptTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.source = Path(self.temp.name) / 'source.wot'
        self.output = Path(self.temp.name) / 'output.wot'
        self.spec = fixture(self.source)

    def test_unicode_roundtrip_and_unrelated_export(self):
        old = self.source.read_bytes()
        report = build(self.source, self.output, self.spec)
        self.assertEqual(entries(self.output)[0]['source'], '按 %s')
        self.assertEqual(body(Package(self.source), 2), body(Package(self.output), 2))
        self.assertTrue(body(Package(self.output), 1).endswith(b'ACTOR_TRAILER'))
        self.assertEqual(restore(self.output.read_bytes(), report), old)
        self.assertEqual(self.source.read_bytes(), old)

    def test_unknown_source_rejected(self):
        self.spec['sha256'] = 'unknown'
        with self.assertRaisesRegex(ValueError, 'Unknown original'):
            build(self.source, self.output, self.spec)

    def test_placeholder_loss_rejected(self):
        self.spec['rows'][0]['translation'] = '按键'
        with self.assertRaisesRegex(ValueError, 'token mismatch'):
            build(self.source, self.output, self.spec)

    def test_missing_and_duplicate_slots_rejected(self):
        for rows in ([], self.spec['rows'] * 2):
            spec = copy.deepcopy(self.spec)
            spec['rows'] = rows
            with self.assertRaisesRegex(ValueError, 'coverage mismatch'):
                build(self.source, self.output, spec)

    def test_logic_field_rejected(self):
        self.spec['rows'][0]['property'] = 'URL'
        with self.assertRaisesRegex(ValueError, 'display string'):
            build(self.source, self.output, self.spec)

    def test_original_output_rejected(self):
        with self.assertRaisesRegex(ValueError, 'output copy'):
            build(self.source, self.source, self.spec)

    def test_tampered_rollback_rejected(self):
        report = build(self.source, self.output, self.spec)
        with self.assertRaisesRegex(ValueError, 'identity differs'):
            restore(self.output.read_bytes() + b'x', report)


class MapInstallPathTests(unittest.TestCase):
    def test_profiled_map_allowed(self):
        import json
        from install import targets
        root=Path(__file__).resolve().parents[1]
        profile=json.loads((root/'profiles/gog-v68.json').read_text('utf8'))
        name='Maps/Tutorial.wot';expected=profile['files'][name]
        bundle=dict(format='localization-bundle-v1',profile=profile['id'],files={name:dict(original_sha256=expected['sha256'],original_size=expected['size'])})
        with tempfile.TemporaryDirectory()as t:
            self.assertIn(name,targets(Path(t).resolve(),bundle))
            bundle['files'][name]['original_sha256']='unknown'
            with self.assertRaisesRegex(ValueError,'Invalid bundle path'):targets(Path(t).resolve(),bundle)

    def test_unknown_map_rejected(self):
        from install import targets
        with tempfile.TemporaryDirectory()as t:
            bundle=dict(format='localization-bundle-v1',profile='gog-v68-observed',files={'Maps/Unknown.wot':{}})
            with self.assertRaisesRegex(ValueError,'Invalid bundle path'):targets(Path(t).resolve(),bundle)
