"""UE1 tables, compact indices, Font pages. Import has no filesystem side effects."""

import struct


class Reader:
    def __init__(self, b, p=0):
        self.b = b
        self.p = p

    def u8(self):
        v = self.b[self.p]
        self.p += 1
        return v

    def i32(self):
        v = struct.unpack_from("<i", self.b, self.p)[0]
        self.p += 4
        return v

    def idx(self):
        a = self.u8()
        v = a & 63
        shift = 6
        more = a & 64
        while more:
            c = self.u8()
            v |= (c & 127) << shift
            shift += 7
            more = c & 128
        return -v if a & 128 else v

    def string(self, ver):
        if ver < 64:
            e = self.b.index(0, self.p)
            s = self.b[self.p : e].decode("cp1252", errors="replace")
            self.p = e + 1
            return s
        n = self.idx()
        z = abs(n) * (2 if n < 0 else 1)
        s = (
            self.b[self.p : self.p + z]
            .decode("utf-16le" if n < 0 else "cp1252", errors="replace")
            .rstrip("\0")
        )
        self.p += z
        return s


class Package:
    def __init__(self, path):
        self.path = path
        self.b = path.read_bytes()
        h = struct.unpack_from("<IHHIiiiiii", self.b)
        assert h[0] == 0x9E2A83C1
        self.ver = h[1]
        self.names = []
        self.imports = []
        self.exports = []
        r = Reader(self.b, h[5])
        for _ in range(h[4]):
            self.names.append(r.string(self.ver))
            r.i32()
        r = Reader(self.b, h[9])
        for _ in range(h[8]):
            self.imports.append(
                dict(cp=r.idx(), cn=r.idx(), outer=r.i32(), name=r.idx())
            )
        r = Reader(self.b, h[7])
        for _ in range(h[6]):
            e = dict(
                cls=r.idx(),
                super=r.idx(),
                outer=r.i32(),
                name=r.idx(),
                flags=r.i32(),
                size=r.idx(),
            )
            e["offset"] = r.idx() if e["size"] else 0
            self.exports.append(e)

    def obj(self, i):
        if i == 0:
            return "None"
        e = self.exports[i - 1] if i > 0 else self.imports[-i - 1]
        return self.names[e["name"]]

    def full(self, i, seen=None):
        if not i:
            return ""
        seen = set() if seen is None else seen
        if i in seen:
            return "<cycle>"
        seen.add(i)
        e = self.exports[i - 1] if i > 0 else self.imports[-i - 1]
        o = self.full(e["outer"], seen)
        return (o + "." if o else "") + self.names[e["name"]]

    def records(self):
        return [
            dict(
                index=i + 1,
                path=self.full(i + 1),
                class_name=self.obj(e["cls"]),
                size=e["size"],
                offset=e["offset"],
            )
            for i, e in enumerate(self.exports)
        ]


def ci(n):
    neg = n < 0
    n = abs(n)
    a = (n & 63) | (128 if neg else 0)
    n >>= 6
    out = bytearray([a | (64 if n else 0)])
    while n:
        a = n & 127
        n >>= 7
        out.append(a | (128 if n else 0))
    return bytes(out)


def body(a, i):
    e = a.exports[i - 1]
    return a.b[e["offset"] : e["offset"] + e["size"]]


def font(b):
    r = Reader(b)
    assert r.idx() == 0
    pages = []
    for _ in range(r.idx()):
        tex = r.idx()
        count = r.idx()
        chars = b[r.p : r.p + 16 * count]
        r.p += 16 * count
        pages.append((tex, count, chars))
    cpp = r.i32()
    assert r.p == len(b)
    return pages, cpp
