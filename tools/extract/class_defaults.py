"""Read v68 UClass default-property streams; source identities are profiled before edits."""
import struct
from tools.pack.ue1 import Package, Reader, body


def tags(data, start, names):
    reader = Reader(data, start)
    result = []
    while True:
        begin = reader.p
        name = reader.idx()
        if not 0 <= name < len(names):
            raise ValueError('Invalid default property name')
        if names[name] == 'None':
            if reader.p != len(data):
                raise ValueError('Default stream has trailing bytes')
            return result
        info_offset = reader.p
        info = reader.u8()
        typ, size_code = info & 15, (info >> 4) & 7
        if not 1 <= typ <= 15:
            raise ValueError('Invalid property type')
        if typ == 10:
            reader.idx()
        if size_code < 5:
            size = (1, 2, 4, 12, 16)[size_code]
        elif size_code == 5:
            size = reader.u8()
        elif size_code == 6:
            size = struct.unpack_from('<H', data, reader.p)[0]
            reader.p += 2
        else:
            size = reader.i32()
        slot_begin = reader.p
        slot = 0
        if typ != 3 and info & 128:
            a = reader.u8()
            if a & 128:
                if a & 64:
                    slot = ((a & 63) << 24) | (reader.u8() << 16) | (reader.u8() << 8) | reader.u8()
                else:
                    slot = ((a & 127) << 8) | reader.u8()
            else:
                slot = a
        if typ == 3:
            size = 0
        end = reader.p + size
        if size < 0 or end > len(data):
            raise ValueError('Property payload outside export')
        row = dict(property=names[name], slot=slot, type=typ, tag_start=begin,
                   info_offset=info_offset, info=info, slot_start=slot_begin,
                   value_start=reader.p, value_end=end)
        if typ == 13:
            value_reader = Reader(data, reader.p)
            row['source'] = value_reader.string(68)
            if value_reader.p != end:
                raise ValueError('FString size mismatch')
        result.append(row)
        reader.p = end


def discover(package, record, property_names):
    """Research-only search. Builds use the recorded offset and full export SHA, not this search."""
    data = body(package, record['index'])
    candidates = []
    for start in range(len(data)):
        try:
            rows = tags(data, start, package.names)
            if rows and all(r['property'] in property_names for r in rows):
                candidates.append((start, rows))
        except (ValueError, IndexError, struct.error, UnicodeError):
            pass
    return min(candidates, key=lambda x: x[0]) if candidates else (len(data)-1, [])
