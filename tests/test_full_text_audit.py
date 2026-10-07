import importlib,json,tempfile,unittest
from pathlib import Path
from tools.extract.int_files import entries,tokens
from tools.validate.full_text_audit import fingerprint,catalog_readback
ROOT=Path(__file__).resolve().parents[1]

class FullTextAuditTests(unittest.TestCase):
 def test_known_escape_does_not_swallow_following_english(self):
  self.assertEqual(tokens(r'\n\nHowever'),[r'\n',r'\n'])
  self.assertEqual(tokens(r'\n\n部分'),[r'\n',r'\n'])
  self.assertEqual(tokens(r'\unknown42'),[r'\unknown42'])
 def test_overlay_preserves_previous_import_and_original(self):
  with tempfile.TemporaryDirectory()as d:
   root=Path(d);src=root/'src';dst=root/'dst';src.mkdir();dst.mkdir()
   p=src/'Sample.int';p.write_text('[UI]\nFirst=Loading\nSecond=Settings\n',encoding='ascii');before=fingerprint(p)
   def row(e,t):
    import hashlib
    return dict(file='Sample.int',section=e['section'],key=e['key'],occurrence=1,translation=t,source_sha256=hashlib.sha256(e['source'].encode()).hexdigest(),source_length=len(e['source']),tokens=tokens(e['source']))
   a,b=entries(p);config={'encoding':'utf-16le-bom','validation':{'max_characters':100},'subtitle_timing':'preserve-source-length'};profile={'subtitle_files':[]};imp=importlib.import_module('tools.import.int_files')
   imp.import_rows(src,[row(a,'正在载入')],dst,config,profile)
   imp.import_rows(src,[row(b,'设置')],dst,config,profile,preserve_existing=True)
   self.assertEqual([r['source']for r in entries(dst/'Sample.int')],['正在载入','设置'])
   self.assertEqual(fingerprint(p),before)
 def test_readback_catches_later_stage_overwrite(self):
  with tempfile.TemporaryDirectory()as d:
   game=Path(d);(game/'System').mkdir()
   (game/'System/Sample.int').write_text('[UI]\nText=Loading\n',encoding='ascii')
   rows=[dict(file='Sample.int',section='UI',key='Text',occurrence=1,translation='正在载入')]
   self.assertEqual(len(catalog_readback(game,rows)),1)
   (game/'System/Sample.int').write_text('[UI]\nText=正在载入\n',encoding='utf-8-sig')
   self.assertEqual(catalog_readback(game,rows),[])
 def test_added_catalog_is_complete_and_placeholder_bound(self):
  rows=json.loads((ROOT/'locales/zh-CN/strings.json').read_text('utf8'));cfg=json.loads((ROOT/'locales/zh-CN/config.json').read_text('utf8'))
  self.assertEqual(importlib.import_module('tools.import.int_files').validate_rows(rows,cfg),0)
  for f,sec,key in [('Engine.int','Progress','Saving'),('Engine.int','Progress','Loading'),('Engine.int','GameInfo','SwitchLevelMessage'),('WoTBrowser.int','WOTBrowserServerPing','GameBegunFalseText'),('Startup.int','General','RecoveryMode')]:
   row=next(r for r in rows if(r['file'],r['section'],r['key'])==(f,sec,key))
   self.assertTrue(any('\u3400'<=c<='\u9fff'for c in row['translation']))

if __name__=='__main__':unittest.main()
