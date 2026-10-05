"""Build an exact-match display fallback from fingerprint-verified sources."""
import hashlib
import json
from pathlib import Path
from tools.pack.ue1 import Package,body
from tools.extract.class_defaults import tags
from tools.extract.int_files import tokens


def bind(game, config, root):
    rows=[]
    profile=json.loads((root/'profiles/package-text.json').read_text('utf8'))
    for row in config.get('package_text_data',{}).get('rows',[]):
        p=Package(game/'System'/row['package'])
        record=next(r for r in p.records()if r['path']==row['cls'] and r['class_name']=='None')
        raw=body(p,record['index']);spec=profile[row['package']][row['cls']]
        if hashlib.sha256(raw).hexdigest()!=spec['export_sha256']:raise ValueError('Unknown runtime message class')
        field=next(t for t in tags(raw,spec['defaults_offset'],p.names)if(t['property'],t['slot'])==(row['property'],row['slot']))
        if hashlib.sha256(field['source'].encode('utf8')).hexdigest()!=row['source_sha256']:raise ValueError('Runtime message source changed')
        rows.append(dict(source=field['source'],translation=row['translation']))
    for row in config.get('runtime_messages_data',{}).get('rows',[]):
        p=Package(game/'System/WOT.u');record=next(r for r in p.records()if r['path']==row['export']);raw=body(p,record['index'])
        if hashlib.sha256(raw).hexdigest()!=row['export_sha256']or b'\x1f'+row['source'].encode('ascii')+b'\0'not in raw:raise ValueError('Unknown runtime message code export')
        rows.append(dict(source=row['source'],translation=row['translation']))
    merged={}
    for row in rows:
        source,target=row['source'],row['translation']
        if tokens(source)!=tokens(target)or any(c in source+target for c in '\r\n\0"'):raise ValueError('Invalid runtime message text/tokens')
        if source in merged and merged[source]!=target:raise ValueError('Ambiguous runtime message translation')
        merged[source]=target
    if len(merged)>32:raise ValueError('Runtime message capacity exceeded')
    return [dict(source=source,translation=target)for source,target in sorted(merged.items())]

