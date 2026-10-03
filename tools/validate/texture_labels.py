"""Static scope verification for texture-label resource patches."""

import argparse
import json
from pathlib import Path
from src.patch.delta import sha
from tools.pack.ue1 import Package, Reader, body
from tools.extract.texture_audit import property_end


def verify(source, profile, manifest=None, baseline=None):
    pkg = Package(source)
    if pkg.ver != profile["package_version"]:
        raise ValueError("Unsupported package version")
    records = {r["path"]: r for r in pkg.records()}
    changes = {r["path"]: r for r in manifest["changes"]} if manifest else {}
    for expected in profile["textures"]:
        path = expected["path"]
        digest = sha(body(pkg, records[path]["index"]))
        target = (
            changes[path]["modified_body_sha256"]
            if manifest
            else expected["body_sha256"]
        )
        if digest != target:
            raise ValueError("Texture fingerprint mismatch: " + path)
    if baseline:
        old = Package(baseline)
        if (
            old.names != pkg.names
            or old.imports != pkg.imports
            or old.exports != pkg.exports
        ):
            raise ValueError("Package tables changed")
        selected = {records[r["path"]]["index"] for r in profile["textures"]}
        if len(old.b) != len(pkg.b):
            raise ValueError("Package size changed")
        for r in old.records():
            if r["index"] not in selected and body(old, r["index"]) != body(
                pkg, r["index"]
            ):
                raise ValueError("Unrelated export changed: " + r["path"])
            if r["index"] in selected:
                before, after = body(old, r["index"]), body(pkg, r["index"])
                end, _ = property_end(before, old.names)
                rr = Reader(before, end)
                if rr.idx() != 1:
                    raise ValueError("Unexpected mip count")
                rr.i32()
                count = rr.idx()
                offset = rr.p
                rr.p += count
                width, height = rr.i32(), rr.i32()
                left, top, right, bottom = changes[r["path"]]["rectangle"]
                allowed = {
                    offset + y * width + x
                    for y in range(top, bottom)
                    for x in range(left, right)
                }
                if len(before) != len(after) or any(
                    a != b and i not in allowed
                    for i, (a, b) in enumerate(zip(before, after))
                ):
                    raise ValueError("Texture bytes outside label panel changed")
    state = "MODIFIED" if manifest else "BASELINE"
    print(
        f"{state} PASS: {len(profile['textures'])} texture bodies verified"
        + ("; unrelated exports/tables/size unchanged" if baseline else "")
    )


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source", type=Path, required=True)
    p.add_argument("--profile", type=Path, required=True)
    p.add_argument("--manifest", type=Path)
    p.add_argument("--baseline", type=Path)
    a = p.parse_args()
    verify(
        a.source,
        json.loads(a.profile.read_text("utf8")),
        json.loads(a.manifest.read_text("utf8")) if a.manifest else None,
        a.baseline,
    )
