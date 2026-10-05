"""Bind a new HUD class through one verified GameInfo default property."""
import hashlib
import struct
from tools.pack.ue1 import Package, Reader, ci, body


def bind(source, output, source_sha256, original_export_sha256, superclass_bindings=None):
    p=Package(source)
    if output.exists() or output.resolve()==source.resolve():raise ValueError('Choose new output copy')
    if hashlib.sha256(p.b).hexdigest()!=source_sha256:raise ValueError('Unknown HUD input')
    rec=next(r for r in p.records()if r['path']=='giWOT' and p.exports[r['index']-1]['cls']==0)
    original=body(p,rec['index'])
    if hashlib.sha256(original).hexdigest()!=original_export_sha256:raise ValueError('GameInfo class fingerprint changed')
    hud=next(r for r in p.records()if r['path']=='MainHUD' and p.exports[r['index']-1]['cls']==0)
    old=ci(p.names.index('HUDType'))+b'\x15'+ci(hud['index'])+b'\0'
    if not original.endswith(old):raise ValueError('HUDType serialized default mismatch')
    names=list(p.names);added=[]
    def ni(n):
        if n not in names:names.append(n);added.append(n)
        return names.index(n)
    imports=[dict(x)for x in p.imports]
    core=ni('Core');pkg=ni('Package');cls=ni('Class');module=ni('SubtitleRuntime');hname=ni('SubtitleHUD')
    imports.append(dict(cp=core,cn=pkg,outer=0,name=module));package_index=-len(imports)
    imports.append(dict(cp=core,cn=cls,outer=package_index,name=hname));new_index=-len(imports)
    value=ci(new_index);newtag=ci(p.names.index('HUDType'))+b'\x55'+bytes([len(value)])+value+b'\0'
    modified=original[:-len(old)]+newtag
    changed = {rec['index']: modified}
    super_changes = {}
    for name, fingerprint in (superclass_bindings or {}).items():
        record = next(r for r in p.records() if r['path']==name and p.exports[r['index']-1]['cls']==0)
        raw = body(p,record['index'])
        if hashlib.sha256(raw).hexdigest()!=fingerprint:
            raise ValueError('Unknown specialized HUD class: '+name)
        if p.exports[record['index']-1]['super']!=hud['index'] or not raw.startswith(ci(hud['index'])):
            raise ValueError('Specialized HUD superclass mismatch: '+name)
        changed[record['index']] = ci(new_index)+raw[len(ci(hud['index'])):]
        super_changes[record['index']] = new_index
    data=bytearray(p.b);exports=[dict(e)for e in p.exports]
    for index, raw in changed.items():
        exports[index-1].update(offset=len(data),size=len(raw))
        if index in super_changes: exports[index-1]['super']=super_changes[index]
        data+=raw
    header=struct.unpack_from('<IHHIiiiiii',p.b);r=Reader(p.b,header[5])
    for _ in p.names:r.string(p.ver);r.i32()
    noff=len(data);data+=p.b[header[5]:r.p]
    for name in added:
        text=name.encode()+b'\0';data+=ci(len(text))+text+struct.pack('<I',0x70010)
    ioff=len(data)
    for e in imports:data+=ci(e['cp'])+ci(e['cn'])+struct.pack('<i',e['outer'])+ci(e['name'])
    eoff=len(data)
    for e in exports:data+=ci(e['cls'])+ci(e['super'])+struct.pack('<i',e['outer'])+ci(e['name'])+struct.pack('<I',e['flags']&0xffffffff)+ci(e['size'])+(ci(e['offset'])if e['size']else b'')
    struct.pack_into('<iiiiii',data,12,len(names),noff,len(exports),eoff,len(imports),ioff)
    struct.pack_into('<ii',data,56,len(exports),len(names))
    output.write_bytes(data);z=Package(output)
    for i in range(1,len(p.exports)+1):
        if i not in changed and (z.exports[i-1]!=p.exports[i-1]or body(z,i)!=body(p,i)):raise ValueError('Non-HUD export changed')
    return dict(field='giWOT.HUDType',before='WOT.MainHUD',after='SubtitleRuntime.SubtitleHUD',specialized_hud_superclasses=list(superclass_bindings or {}),original_class_sha256=original_export_sha256,modified_sha256=hashlib.sha256(data).hexdigest(),other_exports_unchanged=len(p.exports)-len(changed))
