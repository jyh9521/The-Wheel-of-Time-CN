"""Hash-gated UE1 bitmap font scaling on a copy; retain all non-font exports."""
import argparse,hashlib,json,math,struct
from pathlib import Path
from PIL import Image
from tools.pack.ue1 import Package,Reader,body,font,ci
from tools.font.build_font import prop_end

def sha(data):return hashlib.sha256(data).hexdigest()
def scaled(n,ratio):return max(1,math.floor(n*ratio+0.5)) if n else 0

def choose_cpp(capacity):
    if capacity<1:raise ValueError('Glyph exceeds 256px atlas')
    return next(cpp for cpp in [16,8,4,2,1] if cpp<=capacity)

def restore(data,report):
    if sha(data)!=report['modified_sha256']:raise ValueError('Modified package hash differs')
    result=bytes.fromhex(report['header_before'])+data[128:report['original_size']]
    if sha(result)!=report['original_sha256']:raise ValueError('Rollback hash differs')
    return result

def build(source,output,config,manifest):
    if output.exists() or manifest.exists() or output.resolve()==source.resolve():raise ValueError('Choose new copy output paths')
    a=Package(source);ratio=config['scale']
    if sha(a.b)!=config['source_sha256']:raise ValueError('Unknown source package hash')
    if not isinstance(ratio,(float,int)) or not math.isfinite(ratio) or not 1<=ratio<=3:raise ValueError('Scale must be 1..3')
    if struct.unpack_from('<i',a.b,52)[0]!=1:raise ValueError('Inspect multi-generation package first')
    records={r['path']:r for r in a.records() if r['class_name']=='Font'}
    names=config['fonts']
    if len(set(names))!=len(names) or not names or any(n not in records for n in names):raise ValueError('Unknown or duplicate font')
    data=bytearray(a.b);exports=[dict(e) for e in a.exports];added=[];changes=[];cache={}
    def texture(index):
        if index not in cache:
            t=body(a,index);end,tags=prop_end(t)
            if t[end]!=1:raise ValueError('Only single-mip font textures supported')
            r=Reader(t,end+5);n=r.idx();w,h,_,_=struct.unpack_from('<iiBB',t,r.p+n)
            if w*h!=n:raise ValueError('Expected P8 font texture')
            cache[index]=(Image.frombytes('P',(w,h),t[r.p:r.p+n]),t,end,tags)
        return cache[index]
    for name in names:
        record=records[name];fi=record['index'];oldpages,oldcpp=font(body(a,fi));glyphs={}
        for page,(tex,count,rects) in enumerate(oldpages):
            for slot in range(min(count,oldcpp)):
                cp=page*oldcpp+slot;x,y,w,h=struct.unpack_from('<iiii',rects,slot*16)
                if not w or not h:continue
                image,*_=texture(tex)
                if x<0 or y<0 or x+w>image.width or y+h>image.height:raise ValueError('Glyph rectangle outside source texture')
                glyphs[cp]=image.crop((x,y,x+w,y+h)).resize((scaled(w,ratio),scaled(h,ratio)),Image.Resampling.NEAREST)
        if not glyphs:raise ValueError('Empty font')
        cell=max(max(im.size)for im in glyphs.values())+2;columns=256//cell;capacity=columns**2
        new_cpp=choose_cpp(capacity)
        grouped={}
        for cp in sorted(glyphs):grouped.setdefault(cp//new_cpp,[]).append(cp)
        if any(len(cs)>capacity for cs in grouped.values()):raise ValueError('Font page cannot fit 256px atlas')
        groups=[];current=[];count=0
        for page,cs in grouped.items():
            if current and count+len(cs)>capacity:groups.append(current);current=[];count=0
            current.append((page,cs));count+=len(cs)
        if current:groups.append(current)
        newpages=[(0,0,b'')for _ in range(max(grouped)+1)];expected={}
        template_index=oldpages[0][0];_,tb,end,tags=texture(template_index)
        for gi,group in enumerate(groups):
            atlas=Image.new('P',(256,256),0);slot=0;index=len(exports)+1
            for page,cs in group:
                rects=bytearray(new_cpp*16)
                for cp in cs:
                    image=glyphs[cp];x=slot%columns*cell+1;y=slot//columns*cell+1;slot+=1
                    atlas.paste(image,(x,y));struct.pack_into('<iiii',rects,cp%new_cpp*16,x,y,*image.size)
                    expected[cp]=(index,x,y,*image.size)
                newpages[page]=(index,new_cpp,bytes(rects))
            prefix=bytearray(tb[:end])
            for field,value in [('UBits',8),('VBits',8),('USize',256),('VSize',256),('UClamp',256),('VClamp',256)]:
                off,size,_=tags[a.names.index(field)];prefix[off:off+size]=bytes([value]) if size==1 else struct.pack('<i',value)
            payload=atlas.tobytes();offset=len(data)
            packed=bytes(prefix)+b'\x01'+struct.pack('<i',offset+len(prefix)+5+len(ci(len(payload)))+len(payload))+ci(len(payload))+payload+struct.pack('<iiBB',256,256,8,8)
            newname=f'ReadabilityAtlas_{fi}_{gi}'
            if newname in a.names:raise ValueError('Already scaled; use baseline input')
            export=dict(a.exports[template_index-1]);export.update(outer=fi,name=len(a.names)+len(added),size=len(packed),offset=offset)
            exports.append(export);added.append(newname);data+=packed
        fb=b'\0'+ci(len(newpages))+b''.join(ci(t)+ci(c)+rects for t,c,rects in newpages)+struct.pack('<i',new_cpp)
        exports[fi-1].update(size=len(fb),offset=len(data));data+=fb
        changes.append(dict(font=name,export=fi,characters_per_page=new_cpp,glyphs=len(glyphs),atlases=len(groups),maximum_height=max(im.height for im in glyphs.values()),expected=expected))
    h=struct.unpack_from('<IHHIiiiiii',a.b);r=Reader(a.b,h[5])
    for _ in a.names:r.string(a.ver);r.i32()
    name_offset=len(data);data+=a.b[h[5]:r.p]
    for name in added:
        b=name.encode('ascii')+b'\0';data+=ci(len(b))+b+struct.pack('<I',0x70010)
    export_offset=len(data)
    for e in exports:
        data+=ci(e['cls'])+ci(e['super'])+struct.pack('<i',e['outer'])+ci(e['name'])+struct.pack('<I',e['flags'])+ci(e['size'])+(ci(e['offset'])if e['size']else b'')
    struct.pack_into('<iiii',data,12,len(a.names)+len(added),name_offset,len(exports),export_offset)
    struct.pack_into('<ii',data,56,len(exports),len(a.names)+len(added))
    output.parent.mkdir(parents=True,exist_ok=True);output.write_bytes(data);z=Package(output);changed={c['export']for c in changes}
    assert z.imports==a.imports and z.b[36:52]==a.b[36:52]
    for i in range(1,len(a.exports)+1):
        if i not in changed:assert z.exports[i-1]==a.exports[i-1] and body(z,i)==body(a,i)
    for change in changes:
        pages,cpp=font(body(z,change['export']));assert cpp==change['characters_per_page']
        for cp,expected in change.pop('expected').items():
            tex,count,rects=pages[cp//cpp];rect=struct.unpack_from('<iiii',rects,cp%cpp*16);assert (tex,*rect)==expected
            t=body(z,tex);end,_=prop_end(t);r=Reader(t,end+5);n=r.idx();assert struct.unpack_from('<i',t,end+1)[0]==z.exports[tex-1]['offset']+r.p+n
    report=dict(original_sha256=sha(a.b),modified_sha256=sha(data),original_size=len(a.b),header_before=a.b[:128].hex(),scale=ratio,characters_per_page={c['font']:c['characters_per_page'] for c in changes},changes=changes,unchanged_exports=len(a.exports)-len(changed),bytecode_unchanged=True,atlas_limit=256)
    assert restore(bytes(data),report)==a.b
    manifest.write_text(json.dumps(report,indent=2)+'\n',encoding='utf8')
    print(f"FONT SCALE PASS: {ratio}x; {len(changes)} fonts; {len(added)} atlases <=256; {report['unchanged_exports']} other exports unchanged; glyphs/metrics/readback/rollback checked")
    return report

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--config',type=Path,required=True);p.add_argument('--manifest',type=Path,required=True)
    args=p.parse_args();build(args.source,args.out,json.loads(args.config.read_text(encoding='utf8')),args.manifest)
