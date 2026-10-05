"""Append an independently rasterized BMP Font without modifying existing exports."""
import hashlib
import json
import math
import struct
from pathlib import Path
from PIL import Image, ImageFont
from tools.pack.ue1 import Package, Reader, body, ci, font
from tools.font.build_font import prop_end
from tools.font.raster import layout, render


def append_font(source, output, fontpath, config):
    a=Package(source)
    if output.exists() or output.resolve()==source.resolve():raise ValueError('Choose new output')
    if hashlib.sha256(a.b).hexdigest()!=config['source_sha256']:raise ValueError('Unknown font input')
    name=config['name'];size=config['pixel_size'];cpp=64
    if name in a.names or not 8<=size<=32:raise ValueError('Invalid font name or size')
    rec=next(r for r in a.records()if r['path']==config['template'] and r['class_name']=='Font')
    pages,oldcpp=font(body(a,rec['index']))
    cps={page*oldcpp+i for page,(t,n,rects) in enumerate(pages)for i in range(n)if struct.unpack_from('<iiii',rects,i*16)[2]}
    cps={cp for cp in cps if cp>=32}
    f=ImageFont.truetype(str(fontpath),size)
    from fontTools.ttLib import TTFont
    tt=TTFont(str(fontpath));cmap=tt.getBestCmap();tt.close()
    missing=cps-set(cmap)
    if any(cp>=256 for cp in missing):raise ValueError('Source font coverage mismatch')
    chars=[chr(cp)for cp in sorted(cps)]
    metrics=layout(f,[c for c in chars if ord(c) in cmap],size,0,top_padding=1,bottom_padding=1,fit_height=size)
    gw,gh=metrics['width'],metrics['height'];cell=max(gw,gh)+2;columns=256//cell;capacity=columns**2
    groups=[];current=[];count=0
    bypage={p:[c for c in chars if ord(c)//cpp==p]for p in sorted({cp//cpp for cp in cps})}
    for page,cs in bypage.items():
        if len(cs)>capacity:raise ValueError('One font page exceeds atlas capacity')
        if current and count+len(cs)>capacity:groups.append(current);current=[];count=0
        current.append((page,cs));count+=len(cs)
    if current:groups.append(current)
    template=pages[0][0];tb=body(a,template);end,tags=prop_end(tb)
    pi=Reader(tb,tags[a.names.index('Palette')][0]).idx();pb=body(a,pi);pr=Reader(pb);pr.idx();pr.idx()
    palette=[tuple(pb[pr.p+4*k:pr.p+4*k+3])for k in range(256)]
    ink=config.get('ink_rgb',[255,224,96])
    lut=[0]+[min(range(2,256),key=lambda j:sum((palette[j][q]-ink[q]*alpha/255)**2 for q in range(3)))for alpha in range(1,256)]
    data=bytearray(a.b);exports=[dict(e)for e in a.exports];added=[name];fi=len(exports)+1
    fe=dict(a.exports[rec['index']-1]);fe.update(name=len(a.names),outer=0);exports.append(fe)
    newpages=[(0,0,b'')for _ in range(max(bypage)+1)]
    for gi,group in enumerate(groups):
        atlas=Image.new('P',(256,256),0);slot=0;ti=len(exports)+1
        for page,cs in group:
            rects=bytearray(cpp*16)
            for c in cs:
                x=slot%columns*cell+1;y=slot//columns*cell+1;slot+=1
                if ord(c) in missing:
                    ot,on,rs=pages[ord(c)//oldcpp];ox,oy,ow,oh=struct.unpack_from('<iiii',rs,ord(c)%oldcpp*16)
                    raw=body(a,ot);pe,_=prop_end(raw);rr=Reader(raw,pe+5);length=rr.idx();tw,th,_,_=struct.unpack_from('<iiBB',raw,rr.p+length)
                    oldim=Image.frombytes('P',(tw,th),raw[rr.p:rr.p+length])
                    im=oldim.crop((ox,oy,ox+ow,oy+oh)).resize((max(1,round(ow*size/14)),size),Image.Resampling.NEAREST)
                else:
                    mask=render(f,c,metrics)
                    im=Image.frombytes('P',mask.size,bytes(lut[v]for v in mask.tobytes()))
                if max(im.size)>cell-2:raise ValueError("Glyph exceeds atlas cell")
                atlas.paste(im,(x,y));struct.pack_into('<iiii',rects,ord(c)%cpp*16,x,y,*im.size)
            newpages[page]=(ti,cpp,bytes(rects))
        prefix=bytearray(tb[:end])
        for field,val in [('UBits',8),('VBits',8),('USize',256),('VSize',256),('UClamp',256),('VClamp',256)]:
            off,n,_=tags[a.names.index(field)];prefix[off:off+n]=bytes([val])if n==1 else struct.pack('<i',val)
        off=len(data);payload=atlas.tobytes()
        packed=bytes(prefix)+b'\x01'+struct.pack('<i',off+len(prefix)+5+len(ci(len(payload)))+len(payload))+ci(len(payload))+payload+struct.pack('<iiBB',256,256,8,8)
        te=dict(a.exports[template-1]);te.update(outer=fi,name=len(a.names)+len(added),offset=off,size=len(packed))
        exports.append(te);added.append(name+'_Atlas_'+str(gi));data+=packed
    fb=b'\0'+ci(len(newpages))+b''.join(ci(t)+ci(n)+rs for t,n,rs in newpages)+struct.pack('<i',cpp)
    exports[fi-1].update(size=len(fb),offset=len(data));data+=fb
    h=struct.unpack_from('<IHHIiiiiii',a.b);r=Reader(a.b,h[5])
    for _ in a.names:r.string(a.ver);r.i32()
    noff=len(data);data+=a.b[h[5]:r.p]
    for n in added:
        b=n.encode('ascii')+b'\0';data+=ci(len(b))+b+struct.pack('<I',0x70010)
    eoff=len(data)
    for e in exports:data+=ci(e['cls'])+ci(e['super'])+struct.pack('<i',e['outer'])+ci(e['name'])+struct.pack('<I',e['flags']&0xffffffff)+ci(e['size'])+(ci(e['offset'])if e['size']else b'')
    struct.pack_into('<iiii',data,12,len(a.names)+len(added),noff,len(exports),eoff)
    struct.pack_into('<ii',data,56,len(exports),len(a.names)+len(added))
    output.parent.mkdir(parents=True,exist_ok=True);output.write_bytes(data)
    z=Package(output)
    for i in range(1,len(a.exports)+1):
        if z.exports[i-1]!=a.exports[i-1]or body(z,i)!=body(a,i):raise ValueError('Existing export changed')
    return dict(font=name,pixel_size=size,glyphs=len(chars),textures=len(groups),latin_fallback=len(missing),existing_exports_unchanged=len(a.exports),source_sha256=hashlib.sha256(a.b).hexdigest(),modified_sha256=hashlib.sha256(data).hexdigest())
