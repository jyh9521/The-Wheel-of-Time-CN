"""Profiled display-only key labels. Stored bindings and command names stay raw."""

import json
import struct
from pathlib import Path
from tools.pack.ue1 import Package, body, ci
from src.patch.display_expressions import digest, script_header


def rewrite(original, spec, helper):
    if digest(original) != spec["export_sha256"]:
        raise ValueError("Keyboard display export fingerprint mismatch")
    size_offset, start, size = script_header(original)
    if size != spec["script_size"]:
        raise ValueError("Keyboard VM size mismatch")
    edits = spec["edits"]
    for e in edits:
        if original[e["offset"] : e["offset"] + e["size"]].hex() != e["expected_hex"]:
            raise ValueError("Keyboard operand mismatch")
    result = bytearray(original)
    for j in spec["jumps"]:
        if struct.unpack_from("<H", original, j["offset"])[0] != j["target"]:
            raise ValueError("Keyboard jump mismatch")
        target = j["target"] + sum(22 for e in edits if e["vm_start"] < j["target"])
        struct.pack_into("<H", result, j["offset"], target)
    # UCC-owned proof KeyMapped measures 22 additional VM bytes per wrapper.
    # EX_VirtualFunction's serialized compact FName occupies four VM bytes.
    for e in reversed(edits):
        pos = e["offset"]
        operand = original[pos : pos + e["size"]]
        result[pos : pos + e["size"]] = (
            b"\x1b" + ci(helper) + b"\x1fKeyNames\0" + operand + b"\x1fWoT\0\x27\x16"
        )
    struct.pack_into("<i", result, size_offset, size + 22 * len(edits))
    return bytes(result)


def apply(path, labels, spec, report_path):
    if not labels or any(
        not k or not v or any(c in k + v for c in '\r\n\0"=') for k, v in labels.items()
    ):
        raise ValueError("Invalid key display labels")
    if set(labels) != set(spec["keys"]) | {"_"}:
        raise ValueError("Key labels must cover every profiled native key")
    package = Package(path)
    rec = next(r for r in package.records() if r["path"] == spec["export"])
    index = rec["index"]
    original = body(package, index)
    modified = rewrite(original, spec, package.names.index("Localize"))
    data = bytearray(package.b)
    exports = [dict(e) for e in package.exports]
    exports[index - 1].update(offset=len(data), size=len(modified))
    data += modified
    table_offset = len(data)
    for e in exports:
        data += (
            ci(e["cls"])
            + ci(e["super"])
            + struct.pack("<i", e["outer"])
            + ci(e["name"])
            + struct.pack("<I", e["flags"] & 0xFFFFFFFF)
            + ci(e["size"])
        )
        if e["size"]:
            data += ci(e["offset"])
    struct.pack_into("<i", data, 24, table_offset)
    candidate = path.with_suffix(".key-display.u")
    candidate.write_bytes(data)
    reopened = Package(candidate)
    if reopened.names != package.names or reopened.imports != package.imports:
        raise ValueError("Key display changed identity tables")
    for i in range(1, len(exports) + 1):
        if body(reopened, i) != (modified if i == index else body(package, i)):
            raise ValueError("Unexpected keyboard package diff")
    path.write_bytes(candidate.read_bytes())
    candidate.unlink()
    int_path = path.parent / "WoT.int"
    from tools.extract.int_files import decode, encode

    text, encoding = decode(int_path.read_bytes())
    if "[KeyNames]" in text:
        raise ValueError("Existing key label section must not be overwritten")
    text += "\r\n[KeyNames]\r\n" + "".join(f'{k}="{v}"\r\n' for k, v in labels.items())
    int_path.write_bytes(encode(text, encoding))
    report = dict(
        export=spec["export"],
        labels=len(labels),
        original_sha256=digest(original),
        modified_sha256=digest(modified),
        original_vm_size=spec["script_size"],
        modified_vm_size=spec["script_size"] + 22 * len(spec["edits"]),
        bindings_unchanged=True,
        raw_key_arguments_unchanged=True,
    )
    Path(report_path).write_text(json.dumps(report, indent=2), "utf8")
    print(
        f"KEY DISPLAY PASS: {len(labels)} labels; 3 display operands; bindings unchanged"
    )
    return report
