"""Read-only v68 actor MessageTrigger strings; never rebuilds maps."""

import struct
from tools.pack.ue1 import Package, Reader, body


def entries(path):
    package = Package(path)
    if package.ver != 68:
        raise ValueError("Unsupported map version")
    rows = []
    for record in package.records():
        if record["class_name"] != "MessageTrigger":
            continue
        data = body(package, record["index"])
        reader = Reader(data)
        if package.exports[record["index"] - 1]["flags"] & 0x02000000:
            node = reader.idx()
            reader.idx()
            reader.p += 12  # ProbeMask u64, LatentAction i32.
            if node:
                reader.idx()  # Code offset; no extra guessed net-index byte.
        while True:
            name = reader.idx()
            if not 0 <= name < len(package.names):
                raise ValueError("Invalid map property name")
            if package.names[name] == "None":
                break
            info = reader.u8()
            typ, sc = info & 15, (info >> 4) & 7
            if typ == 10:
                reader.idx()
            if sc < 5:
                size = [1, 2, 4, 12, 16][sc]
            elif sc == 5:
                size = reader.u8()
            elif sc == 6:
                size = struct.unpack_from("<H", data, reader.p)[0]
                reader.p += 2
            else:
                size = reader.i32()
            slot = 0
            if typ != 3 and info & 128:
                a = reader.u8()
                if a & 128:
                    if a & 64:
                        slot = (
                            ((a & 63) << 24)
                            | (reader.u8() << 16)
                            | (reader.u8() << 8)
                            | reader.u8()
                        )
                    else:
                        slot = ((a & 127) << 8) | reader.u8()
                else:
                    slot = a
            if typ == 3:
                size = 0
            end = reader.p + size
            if not 0 <= size or end > len(data):
                raise ValueError("Map property outside export")
            if package.names[name] == "Messages":
                if typ != 13:
                    raise ValueError("Unexpected map message type")
                value_reader = Reader(data, reader.p)
                value = value_reader.string(package.ver)
                if value_reader.p != end:
                    raise ValueError("Map message length mismatch")
                rows.append(
                    dict(
                        map=path.name,
                        actor=record["path"],
                        slot=slot,
                        source=value,
                        active=bool(value.strip()) and not value.startswith("//"),
                    )
                )
            reader.p = end
    return rows
