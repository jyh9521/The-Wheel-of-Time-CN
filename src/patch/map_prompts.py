"""Hash-gated map instance text rebuild; geometry, logic and other tags unchanged."""
import hashlib
import struct
from pathlib import Path
from tools.pack.ue1 import Package,body,ci
from tools.extract.map_messages import entries
from tools.extract.int_files import tokens

def sha(data):return hashlib.sha256(data).hexdigest()

def restore(data,report):
    if sha(data)!=report['modified_sha256']:raise ValueError('Modified map identity differs')
    original=bytes.fromhex(report['header_before'])+data[128:report['original_size']]
    if sha(original)!=report['original_sha256']:raise ValueError('Original map restoration mismatch')
    return original

def build(source,output,spec):
    if output.exists() or output.resolve()==source.resolve():raise ValueError("Choose a new output copy")
    p=Package(source)
    if p.ver!=68 or sha(p.b)!=spec['sha256']:raise ValueError('Unknown original map')
    allowed={'Messages','PickupMessage','KeyPickupMessage','Message','StringValue','LockedMessage','UnLockMessage','Content','EditingStr','PlayingStr','ReadyStr','WaitingStr'}
    if not spec["rows"]:raise ValueError("Map message coverage mismatch")
    properties={r.get('property','Messages') for r in spec['rows']}
    if not properties<=allowed:raise ValueError('Only profiled display string fields are supported')
    originals={(r['actor'],r['property'],r['slot']):r for r in entries(source,True,True) if r['active'] and r['property'] in properties}
    translations={(r['actor'],r.get('property','Messages'),r['slot']):r for r in spec['rows']}
    if len(translations)!=len(spec['rows']) or set(translations)!=set(originals):raise ValueError('Map message coverage mismatch')
    changes={};expected={}
    for key,r in originals.items():
        row=translations[key];target=row['translation']
        if sha(r['source'].encode('utf8'))!=row['source_sha256'] or not target or tokens(r['source'])!=tokens(target):raise ValueError('Map prompt source/token mismatch')
        expected[key]=target
        if target==r['source']:
            continue
        payload=ci(-(len(target.encode('utf-16le'))//2+1))+(target+'\0').encode('utf-16le')
        raw=body(p,r['index'])
        tag=raw[r['tag_start']:r['info_offset']]+bytes([(r['info']&128)|0x7d])+struct.pack('<i',len(payload))+raw[r['slot_start']:r['value_start']]+payload
        changes.setdefault(r['index'],[]).append((r['tag_start'],r['value_end'],tag))
    result=bytearray(p.b);exports=[dict(e)for e in p.exports]
    for index,edits in changes.items():
        raw=body(p,index)
        for start,end,tag in sorted(edits,reverse=True):raw=raw[:start]+tag+raw[end:]
        exports[index-1].update(offset=len(result),size=len(raw));result+=raw
    export_offset=len(result)
    for e in exports:
        result+=ci(e['cls'])+ci(e['super'])+struct.pack('<i',e['outer'])+ci(e['name'])+struct.pack('<I',e['flags'])+ci(e['size'])+(ci(e['offset'])if e['size']else b'')
    struct.pack_into('<i',result,24,export_offset)
    output.parent.mkdir(parents=True,exist_ok=True);output.write_bytes(result)
    z=Package(output)
    assert z.names==p.names and z.imports==p.imports and z.b[36:52]==p.b[36:52]
    for i in range(1,len(p.exports)+1):
        if i not in changes:assert z.exports[i-1]==p.exports[i-1] and body(z,i)==body(p,i)
    assert {(r['actor'],r['property'],r['slot']):r['source']for r in entries(output,all_actor_strings=True)if r['active'] and r['property'] in properties}==expected
    report=dict(original_sha256=sha(p.b),modified_sha256=sha(result),original_size=len(p.b),header_before=p.b[:128].hex(),messages=len(expected),changed_actors=len(changes),unchanged_exports=len(p.exports)-len(changes),geometry_and_logic_unchanged=True)
    assert restore(result,report)==p.b
    return report
