"""Regression proof for overlapping duplicates versus independent subtitles."""
import argparse,importlib.util,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
p=argparse.ArgumentParser();p.add_argument('--baseline-model',type=Path);a=p.parse_args()
if a.baseline_model:
    spec=importlib.util.spec_from_file_location('baseline',a.baseline_model);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);Queue=module.CaptionQueue
else:
    from tools.validate.subtitle_display import CaptionQueue as Queue
q=Queue()
for t in [0,.1,.2]:q.add('Hou_18',t,t+30,t)
print('INPUT: same caption delivered at 0, 0.1, 0.2; duration=30; observe=1')
print('ACTIVE:',q.active(1))
if not a.baseline_model:
    assert q.active(1)==['Hou_18'];q.add('Hou_19',1,10,1);assert q.active(2)==['Hou_18','Hou_19']
    assert q.active(30.2)==[];q.add('Hou_18',31,40,31);assert q.active(32)==['Hou_18']
    print('PASS: duplicates merged; different captions retained; expiration and replay retained')
