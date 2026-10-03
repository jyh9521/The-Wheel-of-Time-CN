"""Deterministic P8 UI label rasterization; fixed-size, hash-gated resource edits."""

import argparse
import json
import struct
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from fontTools.ttLib import TTFont
from src.patch.delta import sha
from tools.extract.texture_audit import property_end, decode_texture
from tools.pack.ue1 import Package, Reader, body


def raster_label(image, text, font, spec):
    left, top, right, bottom = spec["rectangle"]
    if not (0 <= left < right <= image.width and 0 < top < bottom < image.height):
        raise ValueError("Label rectangle outside texture")
    box = font.getbbox(text)
    w, h = box[2] - box[0], box[3] - box[1]
    if not text or w > right - left - 4 or h > bottom - top - 2:
        raise ValueError("Label does not fit rectangle: " + repr(text))
    result = image.copy()
    # Reconstruct only the text panel from adjacent unlettered stone rows.
    for x in range(left, right):
        a, b = image.getpixel((x, top - 1)), image.getpixel((x, bottom))
        for y in range(top, bottom):
            t = (y - top + 1) / (bottom - top + 1)
            result.putpixel(
                (x, y), tuple(round(u * (1 - t) + v * t) for u, v in zip(a, b))
            )
    mask = Image.new("L", image.size, 0)
    origin = (
        left + (right - left - w) // 2 - box[0],
        top + (bottom - top - h) // 2 - box[1],
    )
    ImageDraw.Draw(mask).text(origin, text, font=font, fill=255)
    if mask.getbbox() is None:
        raise ValueError("Empty label raster")
    result.paste(tuple(spec["ink_rgb"]), (0, 0, image.width, image.height), mask)
    return result


def build(source, output, fontpath, spec, profile, report, collection_index=0):
    source, output = source.resolve(), output.resolve()
    if source == output:
        raise ValueError("Source and output must differ")
    pkg = Package(source)
    if pkg.ver != profile["package_version"]:
        raise ValueError("Unsupported package version")
    expected = {r["path"]: r for r in profile["textures"]}
    if set(spec["labels"]) != set(expected):
        raise ValueError("Label/profile identities differ")
    records = {r["path"]: r for r in pkg.records()}
    for path, target in expected.items():
        if (
            path not in records
            or sha(body(pkg, records[path]["index"])) != target["body_sha256"]
        ):
            raise ValueError("Unsupported texture body: " + path)
    tt = TTFont(str(fontpath), fontNumber=collection_index)
    cmap = tt.getBestCmap()
    tt.close()
    missing = sorted(
        {c for t in spec["labels"].values() for c in t if ord(c) not in cmap}
    )
    if missing:
        raise ValueError("Missing label glyphs: " + repr(missing))
    font = ImageFont.truetype(str(fontpath), spec["pixel_size"], index=collection_index)
    data = bytearray(pkg.b)
    changes = []
    previews = report.parent / "texture-labels"
    previews.mkdir(parents=True, exist_ok=True)
    for path, text in spec["labels"].items():
        rec = records[path]
        original = body(pkg, rec["index"])
        end, tags = property_end(original, pkg.names)
        offset, size, _ = tags[pkg.names.index("Palette")]
        palette_index = Reader(original[offset : offset + size]).idx()
        if palette_index <= 0:
            raise ValueError("External palette requires separate verified support")
        pb = body(pkg, palette_index)
        pe, _ = property_end(pb, pkg.names)
        pr = Reader(pb, pe)
        if pr.idx() != 256:
            raise ValueError("Unsupported palette")
        colors = [tuple(pb[pr.p + i * 4 : pr.p + i * 4 + 3]) for i in range(256)]
        rr = Reader(original, end)
        if rr.idx() != 1:
            raise ValueError("Only verified single-mip labels supported")
        rr.i32()
        count = rr.idx()
        pixel_offset = rr.p
        rr.p += count
        dimensions = [rr.i32(), rr.i32()]
        if (
            dimensions != expected[path]["dimensions"]
            or count != dimensions[0] * dimensions[1]
        ):
            raise ValueError("Unexpected label dimensions")
        image = decode_texture(pkg, rec, lambda _: None)
        translated = raster_label(image, text, font, spec)
        # Preserve palette, dimensions, mip metadata and every pixel outside panel.
        left, top, right, bottom = spec["rectangle"]
        lut = {}
        for y in range(top, bottom):
            for x in range(left, right):
                rgb = translated.getpixel((x, y))
                if rgb not in lut:
                    lut[rgb] = min(
                        range(1, 256),
                        key=lambda i: sum((a - b) ** 2 for a, b in zip(colors[i], rgb)),
                    )
                data[rec["offset"] + pixel_offset + y * dimensions[0] + x] = lut[rgb]
        changes.append(
            {
                "path": path,
                "index": rec["index"],
                "translation": text,
                "original_body_sha256": sha(original),
                "rectangle": spec["rectangle"],
            }
        )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(data)
    reopened = Package(output)
    changed = {r["index"] for r in changes}
    if (
        reopened.names != pkg.names
        or reopened.exports != pkg.exports
        or reopened.imports != pkg.imports
    ):
        raise ValueError("Package tables changed")
    for rec in pkg.records():
        if rec["index"] not in changed and body(pkg, rec["index"]) != body(
            reopened, rec["index"]
        ):
            raise ValueError("Unrelated export changed")
    for row in changes:
        rec = records[row["path"]]
        row["modified_body_sha256"] = sha(body(reopened, rec["index"]))
        image = decode_texture(reopened, rec, lambda _: None)
        image.save(previews / (row["path"] + ".png"))
    if sha(source.read_bytes()) != sha(pkg.b):
        raise ValueError("Source changed")
    result = {
        "changes": changes,
        "source_sha256": sha(pkg.b),
        "modified_sha256": sha(data),
        "font_sha256": sha(fontpath.read_bytes()),
        "collection_index": collection_index,
        "unrelated_exports_unchanged": True,
        "source_unchanged": True,
        "size_unchanged": len(data) == len(pkg.b),
    }
    report.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", "utf8")
    print(
        f"TEXTURE LABEL PASS: {len(changes)} textures; package size/tables/palettes unchanged; unrelated exports unchanged; source unchanged"
    )
    return result


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    for name in ("source", "output", "font", "config", "profile", "report"):
        p.add_argument("--" + name, type=Path, required=True)
    a = p.parse_args()
    build(
        a.source,
        a.output,
        a.font,
        json.loads(a.config.read_text("utf8")),
        json.loads(a.profile.read_text("utf8")),
        a.report,
    )
