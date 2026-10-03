"""Read-only UE1 indexed texture inventory/export for visual localization audits."""

import argparse
import hashlib
import json
import re
import struct
from pathlib import Path
from PIL import Image, ImageDraw
from tools.pack.ue1 import Package, Reader, body


def property_end(data, names):
    """Property terminator is the package's None name index, not always zero."""
    r = Reader(data)
    tags = {}
    while True:
        ni = r.idx()
        if not 0 <= ni < len(names):
            raise ValueError("Property name index outside name table")
        if names[ni] == "None":
            return r.p, tags
        info = r.u8()
        typ, sc = info & 15, (info >> 4) & 7
        if typ == 10:
            r.idx()
        if sc < 5:
            size = [1, 2, 4, 12, 16][sc]
        elif sc == 5:
            size = r.u8()
        elif sc == 6:
            size = struct.unpack_from("<H", data, r.p)[0]
            r.p += 2
        else:
            size = r.i32()
        if typ != 3 and info & 128:
            ar = r.u8()
            if ar & 128:
                r.p += 3 if ar & 64 else 1
        if typ == 3:
            size = 0
        if size < 0 or r.p + size > len(data):
            raise ValueError("Property payload outside export")
        tags[ni] = (r.p, size, typ)
        r.p += size


def decode_texture(package, record, lookup):
    data = body(package, record["index"])
    end, tags = property_end(data, package.names)

    def value(name, default=None):
        if name not in package.names or package.names.index(name) not in tags:
            return default
        off, size, _ = tags[package.names.index(name)]
        return data[off : off + size]

    fmt = value("Format", b"\0")[0]
    if fmt != 0:
        raise ValueError("Non-P8 texture format " + str(fmt))
    ref = value("Palette")
    if ref is None:
        raise ValueError("No palette property")
    idx = Reader(ref).idx()
    palpackage = package
    if idx < 0:
        full = package.full(idx).split(".")
        palpackage = lookup(full[0])
        path = ".".join(full[1:])
        idx = next(
            r["index"]
            for r in palpackage.records()
            if r["class_name"] == "Palette" and r["path"] == path
        )
    pb = body(palpackage, idx)
    pend, _ = property_end(pb, palpackage.names)
    pr = Reader(pb, pend)
    count = pr.idx()
    if count != 256:
        raise ValueError("Non-256 palette")
    colors = pb[pr.p : pr.p + count * 4]
    rr = Reader(data, end)
    mips = rr.idx()
    if not 1 <= mips <= 16:
        raise ValueError("Invalid mip count")
    if package.ver >= 63:
        rr.i32()
    n = rr.idx()
    pixels = data[rr.p : rr.p + n]
    rr.p += n
    w, h = rr.i32(), rr.i32()
    if not (0 < w <= 8192 and 0 < h <= 8192 and n == w * h):
        raise ValueError("Invalid P8 mip dimensions/payload")
    image = Image.frombytes("P", (w, h), pixels)
    image.putpalette([colors[i * 4 + j] for i in range(256) for j in range(3)])
    return image.convert("RGB")


def map_references(packages):
    """Record map import/placement evidence, not runtime visibility claims."""
    return [
        {
            "map": package.path.name,
            "imports": [
                {"path": package.full(-i - 1), "class": package.names[entry["cn"]]}
                for i, entry in enumerate(package.imports)
                if package.names[entry["cn"]] in ("Texture", "Class")
            ],
            "exports": [
                {"path": r["path"], "class": r["class_name"]} for r in package.records()
            ],
        }
        for package in packages
    ]


def scan(game, out):
    game = game.resolve()
    out = out.resolve()
    if out == game or out.is_relative_to(game):
        raise ValueError("Audit output must be outside original game")
    paths = sorted(
        p
        for folder, suffixes in [
            ("Textures", {".utx"}),
            ("System", {".u"}),
            ("Maps", {".wot", ".unr"}),
        ]
        for p in (game / folder).iterdir()
        if p.suffix.lower() in suffixes
    )
    index = {p.stem.casefold(): p for p in paths}
    cache = {}

    def lookup(name):
        if name.casefold() not in cache:
            cache[name.casefold()] = Package(index[name.casefold()])
        return cache[name.casefold()]

    out.mkdir(parents=True, exist_ok=True)
    images = out / "images"
    images.mkdir(exist_ok=True)
    files = []
    rows = []
    errors = []
    other = []
    for path in paths:
        pkg = lookup(path.stem)
        digest = hashlib.sha256(pkg.b).hexdigest()
        files.append(
            dict(
                file=str(path.relative_to(game)),
                size=len(pkg.b),
                sha256=digest,
                version=pkg.ver,
            )
        )
        for rec in pkg.records():
            if rec["class_name"] != "Texture":
                if rec["class_name"].endswith("Texture"):
                    other.append(dict(file=str(path.relative_to(game)), **rec))
                continue
            identity = dict(file=str(path.relative_to(game)), **rec)
            i = len(rows)
            identity["audit_index"] = i
            identity["candidate"] = bool(
                re.search(
                    "sign|book|scroll|letter|poster|notice|credit|title|logo|banner|label",
                    rec["path"],
                    re.I,
                )
            )
            identity["font_page"] = bool(
                re.search(
                    r"(?:^|\.)(?:F_|Tahoma|UTFont|SmallFont|MedFont|LargeFont|BigFont)",
                    rec["path"],
                )
            )
            try:
                img = decode_texture(pkg, rec, lookup)
                identity["dimensions"] = list(img.size)
                identity["image"] = f"images/{i:05d}.png"
                img.save(out / identity["image"])
            except Exception as e:
                identity["error"] = str(e)
                errors.append(identity)
            rows.append(identity)
    for f in files:
        p = game / f["file"]
        if hashlib.sha256(p.read_bytes()).hexdigest() != f["sha256"]:
            raise ValueError("Source changed during audit")
    sheets = []
    for kind, items, cols, cell in [
        (
            "candidates",
            [r for r in rows if r["candidate"] and not r["font_page"] and "image" in r],
            4,
            (300, 260),
        ),
        (
            "overview",
            [r for r in rows if not r["font_page"] and "image" in r],
            8,
            (180, 190),
        ),
    ]:
        per = cols * 8
        for start in range(0, len(items), per):
            batch = items[start : start + per]
            sheet = Image.new("RGB", (cols * cell[0], 8 * cell[1]), "#dddddd")
            draw = ImageDraw.Draw(sheet)
            for k, row in enumerate(batch):
                x = (k % cols) * cell[0]
                y = (k // cols) * cell[1]
                img = Image.open(out / row["image"])
                img.thumbnail((cell[0] - 8, cell[1] - 40))
                sheet.paste(img, (x + 4, y + 4))
                draw.text(
                    (x + 4, y + cell[1] - 35),
                    str(row["audit_index"]) + " " + Path(row["file"]).name,
                    fill="black",
                )
                draw.text((x + 4, y + cell[1] - 20), row["path"][:28], fill="black")
            name = f"{kind}_{start//per:03d}.jpg"
            sheet.save(out / name, quality=90)
            sheets.append(
                dict(
                    image=name, kind=kind, indices=[row["audit_index"] for row in batch]
                )
            )
    report = dict(
        packages=files,
        textures=rows,
        decode_errors=errors,
        other_texture_classes=other,
        sheets=sheets,
        source_hashes_verified=True,
        scope="All local Texture exports; visual screening is separately documented; not OCR or runtime usage proof",
    )
    (out / "MAP_REFERENCES.json").write_text(
        json.dumps(
            map_references(
                lookup(p.stem) for p in paths if p.suffix.lower() in (".wot", ".unr")
            ),
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        "utf8",
    )
    (out / "INVENTORY.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", "utf8"
    )
    print(
        f"TEXTURE AUDIT: {len(files)} packages; {len(rows)} Texture exports; {len(rows)-len(errors)} decoded; {len(errors)} unsupported; {len(other)} other texture-class exports; {len(sheets)} sheets; original hashes unchanged"
    )
    print(
        "Candidates:",
        [
            (r["audit_index"], r["file"], r["path"])
            for r in rows
            if r["candidate"] and not r["font_page"]
        ],
    )


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--game-dir", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    a = p.parse_args()
    scan(a.game_dir, a.out)
