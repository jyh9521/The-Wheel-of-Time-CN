"""Fingerprint-gated FString class-default edits; executable code stays unchanged."""
import hashlib
import struct
from tools.pack.ue1 import Package, body, ci
from tools.extract.class_defaults import tags
from tools.extract.int_files import tokens


def digest(data):
    return hashlib.sha256(data).hexdigest()


def apply(path, rows, profile):
    package = Package(path)
    if package.ver != 68:
        raise ValueError('Unsupported class defaults version')
    indices = {r['path']: r['index'] for r in package.records() if r['class_name']=='None'}
    changed = {}
    seen = set()
    for cls, spec in profile.items():
        selected = [r for r in rows if r['cls'] == cls]
        if not selected:
            raise ValueError('Class text profile has no translations')
        index = indices[cls]
        raw = body(package, index)
        if digest(raw) != spec['export_sha256']:
            raise ValueError('Unknown default class export: '+cls)
        fields = {(t['property'], t['slot']):t for t in tags(raw,spec['defaults_offset'],package.names)}
        edits = []
        for row in selected:
            key = (cls,row['property'],row['slot'])
            if key in seen:
                raise ValueError('Duplicate class text ID')
            seen.add(key)
            field = fields[(row['property'],row['slot'])]
            target = row['translation']
            if field['type'] != 13 or digest(field['source'].encode('utf8')) != row['source_sha256']:
                raise ValueError('Class FString source changed')
            if not target or '\0' in target or tokens(field['source']) != tokens(target):
                raise ValueError('Class text token mismatch')
            payload = ci(-(len(target.encode('utf-16le'))//2+1))+(target+'\0').encode('utf-16le')
            tag = (raw[field['tag_start']:field['info_offset']]+bytes([(field['info']&128)|0x7d])
                   +struct.pack('<i',len(payload))+raw[field['slot_start']:field['value_start']]+payload)
            edits.append((field['tag_start'],field['value_end'],tag))
        for begin,end,replacement in sorted(edits,reverse=True):
            raw = raw[:begin]+replacement+raw[end:]
        changed[index] = raw
    if len(seen)!=len(rows):
        raise ValueError('Unprofiled class text')
    data = bytearray(package.b)
    exports = [dict(e) for e in package.exports]
    for index,raw in changed.items():
        exports[index-1].update(offset=len(data),size=len(raw));data+=raw
    offset = len(data)
    for e in exports:
        data+=ci(e['cls'])+ci(e['super'])+struct.pack('<i',e['outer'])+ci(e['name'])+struct.pack('<I',e['flags']&0xffffffff)+ci(e['size'])+(ci(e['offset']) if e['size'] else b'')
    struct.pack_into('<i',data,24,offset)
    path.write_bytes(data)
    rebuilt=Package(path)
    for i in range(1,len(package.exports)+1):
        if i not in changed and (body(package,i)!=body(rebuilt,i) or package.exports[i-1]!=rebuilt.exports[i-1]):
            raise ValueError('Unrelated class/code export changed')
    for row in rows:
        spec=profile[row['cls']]
        actual=next(t for t in tags(body(rebuilt,indices[row['cls']]),spec['defaults_offset'],rebuilt.names)
                    if (t['property'],t['slot'])==(row['property'],row['slot']))
        if actual['source']!=row['translation']:
            raise ValueError('Class text read-back mismatch')
    return dict(fields=len(rows),classes=list(profile),original_sha256=digest(package.b),modified_sha256=digest(data),bytecode_unchanged=True)
