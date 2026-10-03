"""WoT resource-only dense BMP builder: CPP64, legacy Latin mappings preserved."""

import argparse, csv, hashlib, json, math, pathlib, struct, sys
from collections import defaultdict
from PIL import Image, ImageDraw, ImageFont
from fontTools.ttLib import TTFont
from tools.pack.ue1 import Package, Reader, ci, body, font


def prop_end(b):
    r = Reader(b)
    tags = {}
    while True:
        ni = r.idx()
        if ni == 0:
            return r.p, tags
        info = r.u8()
        typ = info & 15
        sc = (info >> 4) & 7
        if typ == 10:
            r.idx()
        sizes = [1, 2, 4, 12, 16]
        size = (
            sizes[sc]
            if sc < 5
            else (
                r.u8()
                if sc == 5
                else int.from_bytes(b[r.p : r.p + 2], "little") if sc == 6 else r.i32()
            )
        )
        if sc == 6:
            r.p += 2
        if typ != 3 and info & 128:
            ar = r.u8()
            if ar & 128:
                r.p += 3 if ar & 64 else 1
        if typ == 3:
            size = 0
        tags[ni] = (r.p, size, typ)
        r.p += size


def p2(n):
    return 1 << (max(1, n) - 1).bit_length()


def characters(strings):
    chars = sorted({c for s in strings for c in s if ord(c) >= 256})
    if any(ord(c) > 0xFFFF or 0xD800 <= ord(c) <= 0xDFFF for c in chars):
        raise ValueError("Only BMP Unicode glyphs supported by this engine path")
    if not chars:
        raise ValueError("No non-ASCII glyphs requested")
    return chars


def build(
    source, output, strings, fontpath, manifest, profile, font_config, max_atlas=256
):
    source = source.resolve()
    output = output.resolve()
    manifest = manifest.resolve()
    if output == source:
        raise ValueError("Source and output must differ")
    if max_atlas != 256:
        raise ValueError(
            "Single-mip atlas limit is 256 for the verified renderer; larger atlases need a separately verified mip chain"
        )
    a = Package(source)
    if hashlib.sha256(a.b).hexdigest() != profile["files"]["System/WOT.u"]["sha256"]:
        raise ValueError(
            "Original GOG WOT.u fingerprint differs; inspect new build before patching"
        )
    manifest.parent.mkdir(parents=True, exist_ok=True)
    chars = characters(strings)
    tt = TTFont(str(fontpath), fontNumber=font_config.get("collection_index", 0))
    cmap = tt.getBestCmap()
    missing = [c for c in chars if ord(c) not in cmap]
    tt.close()
    if missing:
        raise ValueError("Source font missing codepoints: " + repr(missing))
    selected = profile["fonts"]
    cpp_new = profile["characters_per_page"]
    data = bytearray(a.b)
    exports = [dict(e) for e in a.exports]
    added = []
    changes = []
    fontindices = []
    bypage = defaultdict(list)
    for c in chars:
        bypage[ord(c) // cpp_new].append(c)
    for rec in a.records():
        if rec["class_name"] != "Font" or rec["path"] not in selected:
            continue
        fi = rec["index"]
        fontindices.append(fi)
        sz = selected[rec["path"]]
        ps, cpp = font(body(a, fi))
        assert cpp == 256 and len(ps) == 1
        oldtex = ps[0][0]
        tb = body(a, oldtex)
        prefix_end, tags = prop_end(tb)
        assert tb[prefix_end] == 1
        palette_tag = tags[a.names.index("Palette")]
        pi = Reader(tb, palette_tag[0]).idx()
        pb = body(a, pi)
        pr = Reader(pb)
        assert pr.idx() == 0 and pr.idx() == 256
        palette = [tuple(pb[pr.p + 4 * k : pr.p + 4 * k + 3]) for k in range(256)]
        lut = [0] + [
            min(
                range(2, 256),
                key=lambda j: sum(
                    (palette[j][q] - v * alpha / 255) ** 2
                    for q, v in enumerate(profile["ink_rgb"])
                ),
            )
            for alpha in range(1, 256)
        ]
        skew = profile.get("oblique", {}).get(rec["path"], 0)
        italic = bool(skew)
        gw = sz + math.ceil((sz - 1) * skew)
        gh = sz
        cell = max(gw, gh) + 2
        capacity = (max_atlas // cell) ** 2
        groups = []
        current = []
        count = 0
        for page, cs in sorted(bypage.items()):
            if len(cs) > capacity:
                raise ValueError("Atlas too small for one Unicode page")
            if current and count + len(cs) > capacity:
                groups.append(current)
                current = []
                count = 0
            current.append((page, cs))
            count += len(cs)
        if current:
            groups.append(current)
        newpages = (
            ps
            + [
                (oldtex, cpp_new, ps[0][2][i * cpp_new * 16 : (i + 1) * cpp_new * 16])
                for i in range(1, 4)
            ]
            + [(0, 0, b"") for _ in range(max(bypage) - 3)]
        )
        glyphs = {}
        textures = []
        f = ImageFont.truetype(
            str(fontpath), sz, index=font_config.get("collection_index", 0)
        )
        baseline_top = f.getbbox(font_config["baseline_anchor"])[1]
        for group_index, group in enumerate(groups):
            total = sum(len(cs) for _, cs in group)
            dim = max(128, p2(math.ceil(math.sqrt(total)) * cell))
            dim = min(dim, max_atlas)
            columns = dim // cell
            assert columns * (dim // cell) >= total
            atlas = Image.new("P", (dim, dim), 0)
            atlas.putpalette(sum((list(c) for c in palette), []))
            pixels = atlas.load()
            slot = 0
            newtex = len(exports) + 1
            for page, cs in group:
                records = bytearray(cpp_new * 16)
                for ch in cs:
                    x = (slot % columns) * cell + 1
                    y = (slot // columns) * cell + 1
                    slot += 1
                    bbox = f.getbbox(ch)
                    mask = Image.new("L", (sz, sz), 0)
                    ImageDraw.Draw(mask).text((0, -baseline_top), ch, font=f, fill=255)
                    if italic:
                        mask = mask.transform(
                            (gw, gh),
                            Image.Transform.AFFINE,
                            (1, skew, -skew * (sz - 1), 0, 1, 0),
                            resample=Image.Resampling.BICUBIC,
                        )
                    if mask.getbbox() is None and not ch.isspace():
                        raise ValueError("Empty raster for " + repr(ch))
                    for yy in range(gh):
                        for xx in range(gw):
                            pixels[x + xx, y + yy] = lut[mask.getpixel((xx, yy))]
                    rect = (x, y, gw, gh)
                    struct.pack_into("<iiii", records, (ord(ch) % cpp_new) * 16, *rect)
                    glyphs[ch] = dict(
                        codepoint=ord(ch),
                        page=page,
                        slot=ord(ch) % cpp_new,
                        texture_export=newtex,
                        rectangle=rect,
                    )
                newpages[page] = (newtex, cpp_new, bytes(records))
            prefix = bytearray(tb[:prefix_end])
            bits = dim.bit_length() - 1
            for name, v in [
                ("UBits", bits),
                ("VBits", bits),
                ("USize", dim),
                ("VSize", dim),
                ("UClamp", dim),
                ("VClamp", dim),
            ]:
                off, size, typ = tags[a.names.index(name)]
                assert size in (1, 4)
                prefix[off : off + size] = (
                    bytes([v]) if size == 1 else struct.pack("<i", v)
                )
            payload = atlas.tobytes()
            off = len(data)
            packed = (
                bytes(prefix)
                + b"\x01"
                + struct.pack(
                    "<i",
                    off + len(prefix) + 1 + 4 + len(ci(len(payload))) + len(payload),
                )
                + ci(len(payload))
                + payload
                + struct.pack("<iiBB", dim, dim, bits, bits)
            )
            data += packed
            name = f"LocaleAtlas_{fi}_{group_index}"
            ne = dict(a.exports[oldtex - 1])
            ne.update(
                outer=fi, name=len(a.names) + len(added), size=len(packed), offset=off
            )
            exports.append(ne)
            added.append(name)
            imagepath = manifest.parent / f'{rec["path"]}_atlas{group_index}.png'
            atlas.convert("RGB").save(imagepath)
            textures.append(
                dict(
                    index=newtex,
                    name=name,
                    dimensions=[dim, dim],
                    glyph_count=total,
                    palette=a.full(pi),
                    preview=imagepath.name,
                )
            )
        fb = (
            b"\0"
            + ci(len(newpages))
            + b"".join(ci(t) + ci(c) + cs for t, c, cs in newpages)
            + struct.pack("<i", cpp_new)
        )
        exports[fi - 1].update(size=len(fb), offset=len(data))
        data += fb
        changes.append(
            dict(
                font=rec["path"],
                export=fi,
                pixel_size=sz,
                baseline_top=baseline_top,
                glyph_style=f"oblique-{skew}" if italic else "upright",
                glyph_dimensions=[gw, gh],
                page_count=len(newpages),
                glyph_count=len(chars),
                glyphs=glyphs,
                textures=textures,
            )
        )
    if len(fontindices) != len(selected):
        raise ValueError("Requested font not found")
    h = struct.unpack_from("<IHHIiiiiii", a.b)
    r = Reader(a.b, h[5])
    for _ in range(h[4]):
        r.string(a.ver)
        r.i32()
    noff = len(data)
    data += a.b[h[5] : r.p]
    for name in added:
        s = name.encode("ascii") + b"\0"
        data += ci(len(s)) + s + struct.pack("<I", 0x70010)
    eoff = len(data)
    for e in exports:
        data += (
            ci(e["cls"])
            + ci(e["super"])
            + struct.pack("<i", e["outer"])
            + ci(e["name"])
            + struct.pack("<I", e["flags"])
            + ci(e["size"])
            + (ci(e["offset"]) if e["size"] else b"")
        )
    struct.pack_into(
        "<iiii", data, 12, len(a.names) + len(added), noff, len(exports), eoff
    )
    generations = struct.unpack_from("<i", data, 52)[0]
    assert generations > 0
    struct.pack_into(
        "<ii", data, 56 + (generations - 1) * 8, len(exports), len(a.names) + len(added)
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(data)
    z = Package(output)
    assert (
        z.names[: len(a.names)] == a.names
        and z.imports == a.imports
        and z.b[36:52] == a.b[36:52]
    )
    for i, e in enumerate(a.exports, 1):
        if i not in fontindices:
            assert z.exports[i - 1] == e and body(z, i) == body(a, i)
        else:
            ps, cpp = font(body(z, i))
            assert ps[0] == font(body(a, i))[0][0] and cpp == cpp_new
            oldpages, oldcpp = font(body(a, i))
            for cp in range(256):
                np = ps[cp // cpp]
                op = oldpages[cp // oldcpp]
                assert (
                    np[0] == op[0]
                    and np[2][(cp % cpp) * 16 : (cp % cpp + 1) * 16]
                    == op[2][(cp % oldcpp) * 16 : (cp % oldcpp + 1) * 16]
                )
            change = next(c for c in changes if c["export"] == i)
            for ch, g in change["glyphs"].items():
                assert ps[g["page"]][0] == g["texture_export"] and struct.unpack_from(
                    "<iiii", ps[g["page"]][2], g["slot"] * 16
                ) == tuple(g["rectangle"])
    for i in range(len(a.exports) + 1, len(z.exports) + 1):
        t = body(z, i)
        end, tags = prop_end(t)
        r = Reader(t, end + 5)
        n = r.idx()
        assert (
            struct.unpack_from("<i", t, end + 1)[0]
            == z.exports[i - 1]["offset"] + r.p + n
        )
    result = dict(
        original="System/WOT.u",
        modified="System/WOT.u",
        original_sha256=profile["files"]["System/WOT.u"]["sha256"],
        modified_sha256=hashlib.sha256(data).hexdigest(),
        glyphs="".join(chars),
        unique_glyphs=len(chars),
        changed_original_exports=len(fontindices),
        unchanged_original_exports=len(a.exports) - len(fontindices),
        added_texture_exports=len(added),
        characters_per_page=cpp_new,
        legacy_256_mappings_preserved=True,
        original_page0_preserved=True,
        bytecode_unchanged=True,
        changes=changes,
    )
    manifest.write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf8"
    )
    print(
        f"FONT BUILD PASS: {len(chars)} glyphs/font; {len(fontindices)} fonts; {len(added)} new textures; {len(a.exports)-len(fontindices)} original exports unchanged; CPP{cpp_new}; original Latin mappings, Page0 and bytecode preserved"
    )
    return result
