"""Static subtitle resource checks and an explicit queue scheduling model."""
import json
import struct
from pathlib import Path
from tools.pack.ue1 import Package,body,font


class CaptionQueue:
    def __init__(self,capacity=64):self.capacity=capacity;self.rows=[]
    def add(self,text,begin,end,now):
        self.rows=[r for r in self.rows if r[2]>now]
        if len(self.rows)>=self.capacity:return False
        self.rows.append((text,begin,end));return True
    def active(self,now):return [r[0]for r in self.rows if r[1]<=now<r[2]]


def verify(baseline,modified,cues):
    a,b=Package(baseline),Package(modified)
    changed=[]
    for r in a.records():
        if body(a,r['index'])!=body(b,r['index']):changed.append(r['path'])
    if set(changed)!={'giWOT','EditorHUD','BattleHUD'}:raise ValueError('Existing exports changed beyond HUD bindings: '+repr(changed))
    for name in ('EditorHUD','BattleHUD'):
        r=next(r for r in b.records()if r['path']==name)
        if b.full(b.exports[r['index']-1]['super'])!='SubtitleRuntime.SubtitleHUD':
            raise ValueError('Specialized HUD bypasses subtitle layer: '+name)
    existing_fonts=[r for r in a.records()if r['class_name']=='Font']
    for r in existing_fonts:
        if body(a,r['index'])!=body(b,r['index']):raise ValueError('UI font changed')
    r=next(r for r in b.records()if r['path']=='SubtitleFont')
    pages,cpp=font(body(b,r['index']));count=0
    for t,n,rs in pages:
        for i in range(n):
            x,y,w,h=struct.unpack_from('<iiii',rs,i*16)
            if w:
                if h!=18 or not 0<=x<x+w<=256 or not 0<=y<y+h<=256:raise ValueError('Subtitle glyph bounds')
                count+=1
    queue=CaptionQueue()
    for c in cues['cues']:queue.add(c['translation'],c['begin'],c['end'],0)
    if len(queue.active(1))!=1 or queue.active(23):raise ValueError('Intro timing/gap regression')
    queue.add('Independent voice',10,20,10)
    if len(queue.active(12))!=2:raise ValueError('Caption overwritten')
    if len(queue.active(24))!=1 or queue.active(31):raise ValueError('Cue expiration regression')
    return dict(existing_ui_fonts_unchanged=len(existing_fonts),subtitle_height=18,subtitle_glyphs=count,queue_model_pass=True,changed_existing_exports=changed,in_game_verified=False)
