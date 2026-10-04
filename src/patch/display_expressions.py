"""Guarded UE1 display-expression adapter; never changes stored boolean values.

Only profiled, straight-line functions are supported. Offsets and argument spans
are version-specific data, not a general-purpose bytecode disassembler.
"""

import hashlib
import json
import struct
import tempfile
from pathlib import Path
from tools.pack.ue1 import Package, Reader, body, ci


def digest(data):
    return hashlib.sha256(data).hexdigest()


def script_header(data):
    reader = Reader(data)
    if reader.idx() != 0:
        raise ValueError("Expected empty function property stream")
    for _ in range(5):  # SuperField, Next, ScriptText, Children, FriendlyName
        reader.idx()
    reader.i32()  # Line
    reader.i32()  # TextPos
    size_offset = reader.p
    size = reader.i32()
    return size_offset, reader.p, size


def replace_casts(original, spec, helper_index):
    if digest(original) != spec['export_sha256']:
        raise ValueError("Original display function fingerprint mismatch")
    size_offset, script_start, size = script_header(original)
    if size != spec['script_size'] or not spec['edits']:
        raise ValueError("Unexpected script size or empty edit list")
    occupied = set()
    for edit in spec['edits']:
        offset = edit['offset']
        expected = b'\x54' + bytes.fromhex(edit['argument_hex'])
        if not script_start <= offset < offset + len(expected) <= len(original) - 7:
            raise ValueError("Display expression outside script")
        if original[offset:offset + len(expected)] != expected:
            raise ValueError("Expected bool-to-string expression mismatch")
        positions = set(range(offset, offset + len(expected)))
        if positions & occupied:
            raise ValueError("Overlapping display expressions")
        occupied |= positions
    result = bytearray(original)
    for edit in sorted(spec['edits'], key=lambda e: e['offset'], reverse=True):
        offset = edit['offset']
        argument = bytes.fromhex(edit['argument_hex'])
        # EX_VirtualFunction, FName, unchanged bool operand, EndFunctionParms.
        result[offset:offset + 1 + len(argument)] = (
            b'\x1b' + ci(helper_index) + argument + b'\x16')
    # FName occupies four VM bytes regardless of compact serialized length.
    # The bundled UCC proof measures +5 VM bytes per wrapped cast.
    struct.pack_into('<i', result, size_offset, size + 5 * len(spec['edits']))
    return bytes(result)


def apply_display_expressions(path, profile, report_path):
    specs = profile.get('display_expressions', [])
    if not specs:
        return []
    package = Package(path)
    if package.ver != 68:
        raise ValueError("Unsupported display package version")
    data = bytearray(package.b)
    exports = [dict(e) for e in package.exports]
    changed = {}
    report = []
    for spec in specs:
        if spec['resource'] != 'System/WOT.u':
            raise ValueError("Unsupported display resource")
        records = [r for r in package.records()
                   if r['path'] == spec['export'] and r['class_name'] == 'Function']
        if len(records) != 1 or package.names.count(spec['helper']) != 1:
            raise ValueError("Display function/helper lookup mismatch")
        record = records[0]
        index = record['index']
        if index in changed:
            raise ValueError("Duplicate display function")
        original = body(package, index)
        modified = replace_casts(original, spec, package.names.index(spec['helper']))
        changed[index] = modified
        exports[index - 1].update(offset=len(data), size=len(modified))
        data += modified
        report.append(dict(export=spec['export'], export_index=index,
                           original_sha256=digest(original),
                           modified_sha256=digest(modified),
                           original_size=len(original), modified_size=len(modified),
                           original_script_size=spec['script_size'],
                           modified_script_size=spec['script_size'] + 5 * len(spec['edits']),
                           helper=spec['helper'], menu_slots=[e['menu_slot'] for e in spec['edits']]))
    export_offset = len(data)
    for e in exports:
        data += (ci(e['cls']) + ci(e['super']) + struct.pack('<i', e['outer'])
                 + ci(e['name']) + struct.pack('<I', e['flags'] & 0xffffffff) + ci(e['size']))
        if e['size']:
            data += ci(e['offset'])
    struct.pack_into('<i', data, 24, export_offset)
    # Validate a separate copy before replacing our generated resource.
    with tempfile.TemporaryDirectory(prefix='display-readback-', dir=path.parent) as temp:
        candidate = Path(temp) / path.name
        candidate.write_bytes(data)
        reopened = Package(candidate)
        if reopened.names != package.names or reopened.imports != package.imports:
            raise ValueError("Display adapter changed names/imports")
        if len(reopened.exports) != len(package.exports):
            raise ValueError("Display adapter changed export count")
        for i, (old, new) in enumerate(zip(package.exports, reopened.exports), 1):
            for key in ('cls', 'super', 'outer', 'name', 'flags'):
                if old[key] != new[key]:
                    raise ValueError("Display adapter changed export metadata")
            if body(reopened, i) != changed.get(i, body(package, i)):
                raise ValueError("Unexpected export body change")
    path.write_bytes(data)
    if path.read_bytes() != bytes(data):
        raise ValueError("Display package read-back mismatch")
    Path(report_path).write_text(json.dumps(dict(
        changed_functions=report, configuration_tokens_unchanged=True,
        all_other_exports_unchanged=True, in_game_verified=False), indent=2) + '\n', 'utf8')
    print(f"MENU VALUE PASS: {sum(len(r['menu_slots']) for r in report)} bool displays; "
          "existing locale helper; setters and all other exports unchanged")
    return report
