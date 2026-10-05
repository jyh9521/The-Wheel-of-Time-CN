import json
import tempfile
import unittest
from pathlib import Path
from tools.validate.subtitle_display import CaptionQueue
from src.patch.delta import create
from install import transaction


class SubtitleDisplayTests(unittest.TestCase):
    def test_concurrent_captions_expire_independently(self):
        q=CaptionQueue();q.add('narrator',0,30,0);q.add('other',5,10,5)
        self.assertEqual(q.active(6),['narrator','other'])
        self.assertEqual(q.active(10),['narrator'])
        self.assertEqual(q.active(30),[])

    def test_future_intro_cues_do_not_replace_first(self):
        root=Path(__file__).resolve().parents[1]
        cues=json.loads((root/'locales/zh-CN/subtitle-cues.json').read_text('utf8'))['cues']
        q=CaptionQueue()
        for c in cues:q.add(c['translation'],c['begin'],c['end'],0)
        self.assertEqual(len(q.active(1)),1)
        self.assertNotIn('第一次',q.active(1)[0])
        self.assertEqual(q.active(23),[])
        self.assertEqual(q.active(24),['第一次试炼，面对的是过去。'])

    def test_full_queue_retains_existing_caption(self):
        q=CaptionQueue(1);q.add('old',0,10,0)
        self.assertFalse(q.add('new',1,5,1));self.assertEqual(q.active(2),['old'])
        self.assertTrue(q.add('later',10,20,10))

    def test_hud_preserves_generic_rendering_and_canvas(self):
        source=(Path(__file__).resolve().parents[1]/'src/runtime/SubtitleRuntime/Classes/SubtitleHUD.uc').read_text('utf8')
        self.assertIn('Super.DrawMessages(C, DeltaTime)',source)
        self.assertIn('C.Font=OldFont',source)
        self.assertIn('C.ClipX=OldClipX',source)
        self.assertNotIn('bSequenceActive = false',source)

    def test_owned_additions_install_restore(self):
        with tempfile.TemporaryDirectory()as t:
            root=Path(t);target=root/'game';target.mkdir()
            bundle=root/'PATCH.json'
            bundle.write_text(json.dumps(dict(format='localization-bundle-v1',files={'System/SubtitleRuntime.u':create(b'',b'own code')},owned_additions=['System/SubtitleRuntime.u'])),'utf8')
            transaction('apply',bundle,target);transaction('verify',bundle,target)
            self.assertEqual((target/'System/SubtitleRuntime.u').read_bytes(),b'own code')
            transaction('restore',bundle,target);self.assertFalse((target/'System/SubtitleRuntime.u').exists())

    def test_unknown_addition_rejected(self):
        from install import targets
        with tempfile.TemporaryDirectory()as t:
            with self.assertRaisesRegex(ValueError,'Unknown owned'):
                targets(Path(t),dict(format='localization-bundle-v1',files={'System/Unknown.u':create(b'',b'x')},owned_additions=['System/Unknown.u']))

    def test_unknown_existing_owned_file_preserved(self):
        with tempfile.TemporaryDirectory()as t:
            root=Path(t);target=root/'game';(target/'System').mkdir(parents=True)
            path=target/'System/SubtitleRuntime.u';path.write_bytes(b'foreign')
            bundle=root/'PATCH.json';bundle.write_text(json.dumps(dict(format='localization-bundle-v1',files={'System/SubtitleRuntime.u':create(b'',b'own')},owned_additions=['System/SubtitleRuntime.u'])),'utf8')
            with self.assertRaises(ValueError):transaction('apply',bundle,target)
            self.assertEqual(path.read_bytes(),b'foreign')

    def test_tampered_addition_preserved_on_restore(self):
        with tempfile.TemporaryDirectory()as t:
            root=Path(t);target=root/'game';target.mkdir()
            bundle=root/'PATCH.json';bundle.write_text(json.dumps(dict(format='localization-bundle-v1',files={'System/SubtitleRuntime.u':create(b'',b'own')},owned_additions=['System/SubtitleRuntime.u'])),'utf8')
            transaction('apply',bundle,target)
            path=target/'System/SubtitleRuntime.u';path.write_bytes(b'tampered')
            with self.assertRaises(ValueError):transaction('restore',bundle,target)
            self.assertEqual(path.read_bytes(),b'tampered')
