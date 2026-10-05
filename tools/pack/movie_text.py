"""Rebuild hash-gated legacy QuickTime text tracks without transcoding media."""
import json
import re
import struct
import unicodedata
from pathlib import Path

from tools.pack.movie_text_probe import atoms, child, sha, restore
from tools.extract.movie_text import decode_sample


def text_tables(data, track_id=None):
    moov = child(data, (b'root', -8, len(data)+8), b'moov')
    for track in atoms(data, moov[1]+8, moov[1]+moov[2]):
        if track[0] != b'trak':
            continue
        tkhd = child(data, track, b'tkhd')
        if data[tkhd[1]+8] != 0:
            raise ValueError('Version-one track header unsupported')
        tid = struct.unpack_from('>I', data, tkhd[1]+20)[0]
        mdia = child(data, track, b'mdia')
        hdlr = child(data, mdia, b'hdlr')
        if data[hdlr[1]+16:hdlr[1]+20] != b'text' or (track_id is not None and tid != track_id):
            continue
        stbl = child(data, child(data, mdia, b'minf'), b'stbl')
        t = {k.decode(): child(data, stbl, k) for k in (b'stsd', b'stsz', b'stco', b'stsc', b'stts')}
        count = struct.unpack_from('>I', data, t['stsz'][1]+16)[0]
        if data[t['stsz'][1]+12:t['stsz'][1]+16] != bytes(4) or t['stsz'][2] != 20+4*count:
            raise ValueError('Expected explicit sample sizes')
        if t['stco'][2] != 16+4*count or struct.unpack_from('>I', data, t['stco'][1]+12)[0] != count:
            raise ValueError('Expected one chunk per text sample')
        desc_count = struct.unpack_from('>I', data, t['stsd'][1]+12)[0]
        descriptions = list(atoms(data, t['stsd'][1]+16, t['stsd'][1]+t['stsd'][2]))
        if len(descriptions) != desc_count or any(a[0] != b'text' for a in descriptions):
            raise ValueError('Invalid text descriptions')
        sc = t['stsc']; sc_count = struct.unpack_from('>I', data, sc[1]+12)[0]
        if sc[2] != 16+12*sc_count or not sc_count:
            raise ValueError('Invalid chunk map')
        sc_rows = [struct.unpack_from('>III', data, sc[1]+16+12*i) for i in range(sc_count)]
        if sc_rows[0][0] != 1 or any(n != 1 or not 1 <= desc <= desc_count for first,n,desc in sc_rows):
            raise ValueError('Only one sample per chunk is supported')
        if any(b[0] <= a[0] for a,b in zip(sc_rows, sc_rows[1:])) or sc_rows[-1][0] > count:
            raise ValueError('Invalid description transition')
        mdhd = child(data, mdia, b'mdhd')
        if mdhd[2] != 32 or data[mdhd[1]+8] != 0:
            raise ValueError('Expected version-zero media header')
        timescale = struct.unpack_from('>I', data, mdhd[1]+20)[0]
        stts = t['stts']; runs = struct.unpack_from('>I',data,stts[1]+12)[0]
        if not timescale or stts[2] != 16+8*runs:
            raise ValueError('Invalid text clock')
        durations = []
        for i in range(runs):
            n,d = struct.unpack_from('>II',data,stts[1]+16+8*i)
            if n > count or d == 0: raise ValueError('Invalid time run')
            durations.extend([d]*n)
        if len(durations) != count: raise ValueError('Text clock count mismatch')
        sizes = struct.unpack_from('>'+str(count)+'I',data,t['stsz'][1]+20)
        offsets = struct.unpack_from('>'+str(count)+'I',data,t['stco'][1]+16)
        mdats = [(a[1]+8,a[1]+a[2]) for a in atoms(data) if a[0] == b'mdat']
        samples=[]; tick=0
        for index,(size,offset,duration) in enumerate(zip(sizes,offsets,durations)):
            if not any(lo <= offset and offset+size <= hi for lo,hi in mdats):
                raise ValueError('Sample outside media payload')
            raw=data[offset:offset+size]; text,encoding=decode_sample(raw)
            samples.append(dict(index=index,sha256=sha(raw),nonempty=bool(text.strip()),
                                begin=tick/timescale,duration=duration/timescale,text=text,raw=raw))
            tick+=duration
        t.update(track=track,track_id=tid,tkhd=tkhd,mdhd=mdhd,count=count,
                 descriptions=descriptions,samples=samples)
        return t
    return None


def read_translations(path):
    result={}
    for line in Path(path).read_text('utf8').splitlines():
        if not line: continue
        key,text=line.split('\t',1); index=int(key)
        if index < 0 or index in result: raise ValueError('Duplicate/negative subtitle ID')
        if not text.strip() or any(ord(c)<32 for c in text): raise ValueError('Empty/control-containing translation')
        if any(0xD800 <= ord(c) <= 0xDFFF for c in text): raise ValueError('Invalid Unicode scalar')
        result[index]=text
    return result


def wrap(text, units=44):
    """Wrap by display units; closing punctuation stays with its preceding glyph."""
    if units < 4: raise ValueError('Invalid line width')
    lines=[];line='';width=0
    closing='，。！？；：、）》】」』…,.!?;:)'
    for c in text:
        w=1 if unicodedata.east_asian_width(c) in 'WF' else 0.5
        if line and width+w>units and c not in closing:
            lines.append(line);line='';width=0
        line+=c;width+=w
    if line:lines.append(line)
    if len(lines)>2:raise ValueError('Caption exceeds two-line capacity')
    return '\r'.join(lines)


def rebuild(data,profile,translations,config):
    if sha(data)!=profile['sha256'] or len(data)!=profile['size']:
        raise ValueError('Unknown movie version: size/SHA-256 mismatch')
    t=text_tables(data,profile['track_id'])
    if not t or t['count']!=len(profile['samples']):raise ValueError('Profile sample count mismatch')
    expected={s['index'] for s in profile['samples'] if s['nonempty']}
    if set(translations)!=expected:raise ValueError('Missing/extra translation IDs')
    chunks=[]
    for observed,known in zip(t['samples'],profile['samples']):
        if observed['sha256']!=known['sha256'] or observed['index']!=known['index']:
            raise ValueError('Source sample identity mismatch')
        text=wrap(translations[observed['index']],config['line_units']) if observed['nonempty'] else ''
        encoded=b'\xfe\xff'+text.encode('utf-16be')
        if len(encoded)>65535:raise ValueError('Text exceeds legacy 16-bit byte length')
        chunks.append(struct.pack('>H',len(encoded))+encoded+struct.pack('>I4sI',12,b'encd',0x100))
    result=bytearray(data);edits=[]
    def edit(offset,new):
        old=bytes(result[offset:offset+len(new)])
        if old!=new:
            edits.append(dict(offset=offset,before=old.hex(),after=new.hex()))
            result[offset:offset+len(new)]=new
    offset=len(data)+8
    for i,raw in enumerate(chunks):
        edit(t['stsz'][1]+20+4*i,struct.pack('>I',len(raw)))
        edit(t['stco'][1]+16+4*i,struct.pack('>I',offset));offset+=len(raw)
    flags=int.from_bytes(data[t['tkhd'][1]+9:t['tkhd'][1]+12],'big')
    edit(t['tkhd'][1]+9,(flags|1).to_bytes(3,'big'))
    language=config['media_language'];height=config['track_height']
    if not isinstance(language,int) or not 0<=language<=32767 or not 40<=height<=128:
        raise ValueError('Invalid media language/track height')
    edit(t['mdhd'][1]+28,struct.pack('>H',language))
    edit(t['tkhd'][1]+88,struct.pack('>I',height<<16))
    for desc in t['descriptions']:
        before=config['source_font'].encode('ascii');after=config['font'].encode('ascii')
        if len(before)!=len(after) or len(before)>255:raise ValueError('Font must fit original Pascal slot')
        body=data[desc[1]:desc[1]+desc[2]];needle=bytes([len(before)])+before
        if body.count(needle)!=1:raise ValueError('Unexpected default font')
        if body[30:38]!=struct.pack('>hhhh',0,0,20,640):raise ValueError('Unknown text rectangle')
        edit(desc[1]+body.index(needle)+1,after)
        edit(desc[1]+34,struct.pack('>h',height))
    if any(struct.unpack_from('>I',data,a[1])[0]==0 for a in atoms(data)):
        raise ValueError('Cannot append after unbounded atom')
    payload=b''.join(chunks);result.extend(struct.pack('>I4s',len(payload)+8,b'mdat')+payload)
    result=bytes(result);readback=text_tables(result,t['track_id'])
    for i,s in enumerate(readback['samples']):
        wanted=wrap(translations[i],config['line_units']) if i in translations else ''
        if s['text']!=wanted:raise ValueError('Unicode read-back mismatch')
        if s['begin']!=t['samples'][i]['begin'] or s['duration']!=t['samples'][i]['duration']:
            raise ValueError('Subtitle timing changed')
    for a in atoms(data):
        if a[0]==b'mdat' and result[a[1]:a[1]+a[2]]!=data[a[1]:a[1]+a[2]]:
            raise ValueError('Original media changed')
    manifest=dict(source_sha256=sha(data),output_sha256=sha(result),source_size=len(data),
                  output_size=len(result),edits=edits,track_id=t['track_id'],samples=t['count'],
                  translated=len(translations),field='First text track: Unicode samples, font, language, two-line bounds',
                  original_media_unchanged=True,timing_unchanged=True)
    if restore(result,manifest)!=data:raise ValueError('Rollback self-check failed')
    return result,manifest
