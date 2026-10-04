"""Guarded credits default-array rebuilding. Original contributors are retained."""
import json
import struct
from pathlib import Path
from src.patch.display_expressions import digest
from tools.pack.ue1 import Package, Reader, body, ci


def read_rows(data, start, name_index):
    reader = Reader(data, start)
    rows = []
    while (name := reader.idx()):
        if name != name_index:
            raise ValueError('Unexpected credits property')
        info = reader.u8()
        if info & 15 != 13:
            raise ValueError('Expected FString credits property')
        sc = (info >> 4) & 7
        if sc < 5:
            size = [1, 2, 4, 12, 16][sc]
        elif sc == 5:
            size = reader.u8()
        elif sc == 6:
            size = struct.unpack_from('<H', data, reader.p)[0]
            reader.p += 2
        else:
            size = reader.i32()
        slot = 0
        if info & 128:
            slot = reader.u8()
            if slot & 128:
                slot = ((slot & 127) << 8) | reader.u8()
        begin = reader.p
        text = reader.string(68)
        if reader.p != begin + size:
            raise ValueError('Credits FString payload size mismatch')
        rows.append((slot, text))
    if reader.p != len(data):
        raise ValueError('Unexpected data after credits defaults')
    return rows


def write_rows(rows, name_index):
    result = bytearray()
    for slot, text in rows:
        if not 0 <= slot < 16384 or '\0' in text:
            raise ValueError('Invalid credits slot/text')
        payload = ci(-(len(text) + 1)) + (text + '\0').encode('utf-16le')
        flag = 128 if slot else 0
        if len(payload) < 256:
            tag = bytes([0x5d | flag, len(payload)])
        else:
            tag = bytes([0x6d | flag]) + struct.pack('<H', len(payload))
        index = (bytes([slot]) if slot < 128 else bytes([0x80 | (slot >> 8), slot & 255])) if slot else b''
        result += ci(name_index) + tag + index + payload
    return bytes(result + b'\0')


def apply(path, locale_data, profile, report_path, terminology=None):
    package = Package(path)
    spec = profile['credits']
    indices = {r['path']: r['index'] for r in package.records()}
    changed = {}
    for name, expected in spec['exports'].items():
        data = body(package, indices[name])
        if digest(data) != expected:
            raise ValueError('Unknown credits export: ' + name)
    original = body(package, indices['Credits'])
    name_index = package.names.index('CreditsText')
    source = read_rows(original, spec['defaults_offset'], name_index)
    data = locale_data if isinstance(locale_data, dict) else json.loads(Path(locale_data).read_text('utf8'))
    rows = data['rows']
    if [r['slot'] for r in rows] != list(range(206)) or len(source) != 204:
        raise ValueError('Credits slots must preserve all 204 original rows and add two rows')
    for (slot, text), row in zip(source, rows):
        if row['slot'] != slot or digest(text.encode('utf8')) != row['source_sha256']:
            raise ValueError('Credits source hash/slot mismatch')
        if ' - ' in text and text.split(' - ', 1)[1] != row['translation'].split(' - ', 1)[-1]:
            raise ValueError('Original contributor name changed')
        if text.count('@') != row['translation'].count('@'):
            raise ValueError('Credits quote markers changed')
        if terminology:
            from tools.validate.terminology import matches
            for english, target in matches(text.split(' - ', 1)[0], terminology):
                if target not in row['translation']:
                    raise ValueError('Credits glossary mismatch: ' + english)
    changed[indices['Credits']] = original[:spec['defaults_offset']] + write_rows(
        [(r['slot'], r['translation']) for r in rows], name_index)
    prop = bytearray(body(package, indices['Credits.CreditsText']))
    if struct.unpack_from('<i', prop, spec['dimension_offset'])[0] != 204:
        raise ValueError('Unexpected credits array dimension')
    struct.pack_into('<i', prop, spec['dimension_offset'], 206)
    changed[indices['Credits.CreditsText']] = bytes(prop)
    script = bytearray(body(package, indices['Credits.PostRender']))
    for offset in spec['array_count_offsets']:
        if script[offset:offset + 2] != b'\x2c\xcc':
            raise ValueError('Unexpected credits ArrayCount expression')
        script[offset + 1] = 206
    changed[indices['Credits.PostRender']] = bytes(script)
    exports = [dict(e) for e in package.exports]
    output = bytearray(package.b)
    for index, rebuilt in changed.items():
        exports[index - 1].update(size=len(rebuilt), offset=len(output))
        output += rebuilt
    offset = len(output)
    for e in exports:
        output += ci(e['cls']) + ci(e['super']) + struct.pack('<i', e['outer']) + ci(e['name'])
        output += struct.pack('<I', e['flags'] & 0xffffffff) + ci(e['size'])
        if e['size']:
            output += ci(e['offset'])
    struct.pack_into('<i', output, 24, offset)
    path.write_bytes(output)
    rebuilt = Package(path)
    if rebuilt.names != package.names or rebuilt.imports != package.imports or len(rebuilt.exports) != len(exports):
        raise ValueError('Credits changed package tables')
    for index in range(1, len(exports) + 1):
        if body(rebuilt, index) != changed.get(index, body(package, index)):
            raise ValueError('Credits changed an unrelated export')
    if read_rows(body(rebuilt, indices['Credits']), spec['defaults_offset'], name_index) != [(r['slot'], r['translation']) for r in rows]:
        raise ValueError('Credits readback mismatch')
    report = dict(rows=206, original_rows_retained=204, attribution=rows[-1]['translation'],
                  changed_exports=list(spec['exports']), pending_terms=data['pending_terms'], in_game_verified=False)
    Path(report_path).write_text(json.dumps(report, indent=2, ensure_ascii=False) + '\n', 'utf8')
    print('CREDITS PASS: 204 original rows retained; 206 rebuilt rows; original contributors retained; attribution appended')
    return report
