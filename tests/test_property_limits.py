import json
import unittest
from pathlib import Path
from src.patch.property_limits import maximum_lookup, setter_stub, slider_stub


class PropertyLimitsTests(unittest.TestCase):
    def setUp(self):
        self.spec=json.loads(Path('profiles/gog-v68.json').read_text())['native_properties']

    def test_semantic_not_byte_maxima(self):
        limits={x['property']:x['maximum']for x in self.spec['integer_limits']}
        self.assertEqual(limits,dict(MasterDetailLevel=2,MaxDetailLevel=4,GoreDetailLevel=3,MaxNumDecals=4095))
        for x in self.spec['integer_limits']:
            self.assertEqual((x['package'],x['owner'],x['minimum']),('Engine','Client',0))
            self.assertTrue(x['evidence'])

    def test_unrelated_255_properties_excluded(self):
        limits={x['property']for x in self.spec['integer_limits']}
        self.assertTrue(limits.isdisjoint({'SoundVolume','MusicVolume','ParticleDensity'}))

    def test_pic_lookup(self):
        a=maximum_lookup(self.spec['integer_limits'],0x11065000,0x11054734)
        b=maximum_lookup(self.spec['integer_limits'],0x21065000,0x21054734)
        self.assertEqual(a,b)

    def test_profiled_sites_guard_original_instructions(self):
        self.assertEqual([x['expected_hex']for x in self.spec['range_sites']],['68ff000000','8b4d088965f0'])

    def test_reject_path_does_not_modify_input_text(self):
        code=setter_stub(0x11065000,0x11064000,0x11018d06,0x11018d1d)
        self.assertTrue(code.startswith(bytes.fromhex('8965f0')))
        # No MOV [EDI],AX or MOV [EDI],EAX: incoming text is read-only.
        self.assertNotIn(bytes.fromhex('668907'),code)
        self.assertNotIn(bytes.fromhex('8907'),code)

    def test_invalid_limits_rejected(self):
        for mutate in [dict(maximum=65536),dict(minimum=1),dict(owner='Other')]:
            limits=[dict(x)for x in self.spec['integer_limits']];limits[0].update(mutate)
            with self.assertRaises(ValueError):maximum_lookup(limits,0x11065000,0x11054734)
