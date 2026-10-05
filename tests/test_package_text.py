import copy
import struct
import tempfile
import unittest
from pathlib import Path
from tools.pack.ue1 import ci,Package,body
from tools.extract.class_defaults import tags,discover
from src.patch.package_text import apply,digest


def fixture(path):
    names=['None','KeyPickupMessage','Key','Code']
    data=bytearray(128);noff=len(data)
    for n in names:
        text=n.encode()+b'\0';data+=ci(len(text))+text+struct.pack('<i',0)
    raw=b'CLASS_HEADER'+ci(1)+b'\x5d\x10'+ci(15)+b'Found key: %s\0\0'+b'\0'
    # Compute the exact FString size rather than a fixed UTF-16 byte assumption.
    payload=ci(14)+b'Found key: %s\0'
    raw=b'CLASS_HEADER'+ci(1)+b'\x7d'+struct.pack('<i',len(payload))+payload+b'\0'
    off=len(data);data+=raw;codeoff=len(data);data+=b'ORIGINAL_BYTECODE'
    eoff=len(data)
    for name,offset,size in [(2,off,len(raw)),(3,codeoff,17)]:
        data+=ci(0)+ci(0)+struct.pack('<i',0)+ci(name)+struct.pack('<I',0)+ci(size)+ci(offset)
    struct.pack_into('<IHHIiiiiii',data,0,0x9e2a83c1,68,0,0,len(names),noff,2,eoff,0,noff)
    path.write_bytes(data)
    return [dict(cls='Key',property='KeyPickupMessage',slot=0,source_sha256=digest(b'Found key: %s'),translation='获得钥匙：%s')],dict(Key=dict(defaults_offset=12,export_sha256=digest(raw)))


class PackageTextTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.path=Path(self.temp.name)/'copy.u';self.rows,self.profile=fixture(self.path)

    def test_defaults_unicode_and_bytecode_preserved(self):
        old=Package(self.path)
        report=apply(self.path,self.rows,self.profile)
        new=Package(self.path)
        self.assertEqual(tags(body(new,1),12,new.names)[0]['source'],'获得钥匙：%s')
        self.assertEqual(body(old,2),body(new,2))
        self.assertTrue(report['bytecode_unchanged'])

    def test_unknown_class_rejected(self):
        self.profile['Key']['export_sha256']='unknown'
        with self.assertRaisesRegex(ValueError,'Unknown default'):apply(self.path,self.rows,self.profile)

    def test_placeholder_loss_rejected(self):
        self.rows[0]['translation']='获得钥匙'
        with self.assertRaisesRegex(ValueError,'token mismatch'):apply(self.path,self.rows,self.profile)

    def test_duplicate_id_rejected(self):
        with self.assertRaisesRegex(ValueError,'Duplicate'):apply(self.path,self.rows*2,self.profile)

    def test_source_hash_rejected(self):
        self.rows[0]['source_sha256']='unknown'
        with self.assertRaisesRegex(ValueError,'source changed'):apply(self.path,self.rows,self.profile)

    def test_trailing_data_rejected(self):
        with self.assertRaisesRegex(ValueError,'trailing'):tags(b'\0EXTRA',0,['None'])

    def test_profile_has_all_confirmed_key_types(self):
        import json
        root=Path(__file__).resolve().parents[1]
        rows=json.loads((root/'locales/zh-CN/package-text.json').read_text('utf8'))['rows']
        self.assertEqual({r['cls']for r in rows if r['property']=='KeyPickupMessage'}, {'Key','KeyShort','KeyMedium','KeyLong','KeyRing'})

    def test_editor_and_battle_use_dedicated_parent(self):
        import json
        root=Path(__file__).resolve().parents[1]
        spec=json.loads((root/'profiles/subtitle-runtime.json').read_text('utf8'))
        self.assertEqual(set(spec['specialized_hud_superclasses']),{'EditorHUD','BattleHUD'})
