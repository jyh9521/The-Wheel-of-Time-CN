"""Version-guarded, equal-size numeric resource edits. No executable patches."""

import hashlib
import math
import struct
from tools.pack.ue1 import Package, body


def edit_bytes(source, edits):
    """Validate all expected fields and contexts before changing an independent copy."""
    data = bytearray(source)
    occupied = set()
    for edit in edits:
        offset = edit["offset"]
        if (
            edit["type"] != "float32-le"
            or type(offset) is not int
            or not 0 <= offset <= len(source) - 4
        ):
            raise ValueError("Invalid resource field")
        if not math.isfinite(edit["value"]) or not 0 <= edit["value"] <= 256:
            raise ValueError("Invalid display margin")
        expected = struct.pack("<f", edit["expected"])
        if source[offset : offset + 4] != expected:
            raise ValueError("Expected original field mismatch")
        start = edit["context_offset"]
        context = bytes.fromhex(edit["context_hex"])
        if (
            type(start) is not int
            or start < 0
            or source[start : start + len(context)] != context
        ):
            raise ValueError("Expected resource context mismatch")
        positions = set(range(offset, offset + 4))
        if occupied & positions:
            raise ValueError("Overlapping resource fields")
        occupied |= positions
    for edit in edits:
        offset = edit["offset"]
        data[offset : offset + 4] = struct.pack("<f", edit["value"])
    assert len(data) == len(source)
    assert all(
        a == b for i, (a, b) in enumerate(zip(source, data)) if i not in occupied
    )
    return bytes(data)


def apply_resource_edits(path, profile):
    edits = profile.get("resource_edits", [])
    if not edits:
        return []
    package = Package(path)
    data = bytearray(package.b)
    results = []
    seen_exports = set()
    for edit in edits:
        if edit["resource"] != "System/WOT.u":
            raise ValueError("Resource adapter only supports WOT.u")
        matches = [r for r in package.records() if r["path"] == edit["export"]]
        if len(matches) != 1:
            raise ValueError("Resource export mismatch")
        record = matches[0]
        if record["index"] in seen_exports:
            raise ValueError("Use one guarded edit per resource export")
        seen_exports.add(record["index"])
        original = body(package, record["index"])
        if hashlib.sha256(original).hexdigest() != edit["export_sha256"]:
            raise ValueError("Original export fingerprint mismatch")
        modified = edit_bytes(original, [edit])
        start = record["offset"]
        data[start : start + len(original)] = modified
        results.append(
            dict(
                edit,
                export_index=record["index"],
                absolute_offset=start + edit["offset"],
                modified_export_sha256=hashlib.sha256(modified).hexdigest(),
            )
        )
    # Verify the entire resource diff is limited to explicitly allowed float fields.
    allowed = {r["absolute_offset"] + j for r in results for j in range(4)}
    assert all(
        a == b for i, (a, b) in enumerate(zip(package.b, data)) if i not in allowed
    )
    path.write_bytes(data)
    if path.read_bytes() != bytes(data):
        raise ValueError("Resource field read-back mismatch")
    print(
        f"RESOURCE FIELD PASS: {len(results)} display-only fields; size and package tables unchanged"
    )
    return results
