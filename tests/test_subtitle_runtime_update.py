import hashlib,json,tempfile,unittest
from pathlib import Path
from tools.build.update_subtitle_runtime import update

def digest(b):return hashlib.sha256(b).hexdigest()
class RuntimeUpgradeTests(unittest.TestCase):
    def fixture(self,root):
        game=root/'game';(game/'System').mkdir(parents=True);(game/'System/SubtitleRuntime.u').write_bytes(b'old')
        original={'format':'player-test-v1','files':[{'path':'System/SubtitleRuntime.u','owned':True,'modified_size':3,'modified_sha256':digest(b'old')}]}
        changed={'format':'player-test-v1','files':[{'path':'System/SubtitleRuntime.u','owned':True,'modified_size':3,'modified_sha256':digest(b'new')}]}
        old=root/'old.json';new=root/'new.json';old.write_text(json.dumps(original));new.write_text(json.dumps(changed))
        state=game/'backup/STATE.json';state.parent.mkdir(parents=True);state.write_text(json.dumps({'manifest_sha256':digest(old.read_bytes()),'config':[]}))
        replacement=root/'replacement.u';replacement.write_bytes(b'new')
        return game,old,new,replacement,root/'receipt'
    def test_upgrade_and_exact_rollback(self):
        with tempfile.TemporaryDirectory() as tmp:
            args=self.fixture(Path(tmp));state=args[0]/'backup/STATE.json';before=state.read_bytes()
            update(*args);self.assertEqual((args[0]/'System/SubtitleRuntime.u').read_bytes(),b'new')
            update(*args,restore=True);self.assertEqual(state.read_bytes(),before);self.assertEqual((args[0]/'System/SubtitleRuntime.u').read_bytes(),b'old')
    def test_external_edit_rejected_without_backup(self):
        with tempfile.TemporaryDirectory() as tmp:
            args=self.fixture(Path(tmp));(args[0]/'System/SubtitleRuntime.u').write_bytes(b'bad')
            with self.assertRaises(ValueError):update(*args)
            self.assertFalse(args[-1].exists())
    def test_changed_other_resource_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            args=self.fixture(Path(tmp));data=json.loads(args[2].read_text());data['files'].append({'path':'System/WOT.u'});args[2].write_text(json.dumps(data))
            with self.assertRaises(ValueError):update(*args)
            self.assertEqual((args[0]/'System/SubtitleRuntime.u').read_bytes(),b'old')
