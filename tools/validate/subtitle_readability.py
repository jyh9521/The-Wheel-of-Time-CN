"""Read-only subtitle font audit and pixel-size preview; never patch/launch a game."""
import argparse,collections,hashlib,json,struct
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
from fontTools.ttLib import TTFont
from tools.pack.ue1 import Package,body,font

def audit(game,font_path,out):
    required='1080p 字幕字号对照：14 / 24 / 28 / 32 px字号预览，不是游戏截图；不代表游戏换行与裁切已通过。第一次试炼，面对的是过去。归途只会出现一次。坚定你的意志。'
    with TTFont(font_path) as face:
        missing=set(map(ord,required))-set(face.getBestCmap())
    if missing:raise ValueError('Preview font missing codepoints: '+repr(sorted(missing)))
    out.mkdir(parents=True,exist_ok=False)
    package_path=game/'System/WOT.u';before=package_path.read_bytes();pkg=Package(package_path)
    record=next(r for r in pkg.records() if r['path']=='F_WOTReg14' and r['class_name']=='Font')
    pages,cpp=font(body(pkg,record['index']));metrics=collections.Counter()
    for _,_,data in pages:
        for at in range(0,len(data),16):
            _,_,w,h=struct.unpack_from('<iiii',data,at)
            if w and h:metrics[(w,h)]+=1
    image=Image.new('RGB',(1920,1080),(22,24,28));draw=ImageDraw.Draw(image)
    title=ImageFont.truetype(str(font_path),32)
    draw.text((64,34),'1080p 字幕字号对照：14 / 24 / 28 / 32 px',font=title,fill='white')
    draw.text((64,85),'字号预览，不是游戏截图；不代表游戏换行与裁切已通过。',font=ImageFont.truetype(str(font_path),22),fill=(170,180,190))
    sample='第一次试炼，面对的是过去。归途只会出现一次。坚定你的意志。'
    for i,size in enumerate([14,24,28,32]):
        y=180+i*205
        draw.text((64,y),str(size)+' px',font=title,fill=(200,200,200))
        draw.rectangle((192,y+55,1728,y+150),fill=(8,10,12))
        f=ImageFont.truetype(str(font_path),size)
        draw.text((220,y+80),sample,font=f,fill=(255,228,116))
    image.save(out/'SIZE_PREVIEW.png')
    report=dict(game_package_sha256=hashlib.sha256(before).hexdigest(),font=record['path'],characters_per_page=cpp,pages=len(pages),
        glyph_metrics=[dict(width=w,height=h,count=n)for (w,h),n in metrics.most_common()],
        preview_sizes=[14,24,28,32],preview_resolution=[1920,1080],
        font_source_sha256=hashlib.sha256(font_path.read_bytes()).hexdigest(),
        game_launched=False,game_modified=False,preview_is_game_render=False)
    (out/'AUDIT.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    assert package_path.read_bytes()==before
    assert Image.open(out/'SIZE_PREVIEW.png').size==(1920,1080)
    assert json.loads((out/'AUDIT.json').read_text(encoding='utf8'))==report
    print('SUBTITLE READABILITY AUDIT PASS: package unchanged; 1920x1080 preview; original glyph metrics recorded; no game launch')

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--game-dir',type=Path,required=True);p.add_argument('--font',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();audit(a.game_dir,a.font,a.out)
