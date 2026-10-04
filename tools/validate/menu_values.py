"""Narrow VM scanner for profiled menu value expressions; unknown tokens fail."""

import argparse
import json
from pathlib import Path
from tools.pack.ue1 import Package, body, Reader
from src.patch.display_expressions import script_header, digest, replace_casts


def scan_vm(data, positions=None):
    _, start, size = script_header(data)
    reader = Reader(data, start)
    vm, boundaries, targets = 0, set(), []

    def byte():
        nonlocal vm
        vm += 1
        return reader.u8()

    def expression():
        nonlocal vm
        boundaries.add(vm)
        if positions is not None:
            positions[reader.p] = vm
        op = byte()
        if op in (0, 1):
            reader.idx()
            vm += 4
        elif op in (15, 26):
            expression()
            expression()
        elif op in (6, 7):
            targets.append((reader.p, int.from_bytes(data[reader.p : reader.p + 2], "little")))
            reader.p += 2
            vm += 2
            if op == 7:
                expression()
        elif op == 31:
            while byte():
                pass
        elif op in (37, 38, 39, 40, 11):
            pass
        elif op in (36, 44):
            byte()
        elif op == 46:
            reader.idx()
            vm += 4
            expression()
        elif op == 25:
            expression()
            reader.p += 3
            vm += 3
            expression()
        elif op in (45, 74, 75, 83, 84):
            expression()
        elif op == 27 or op >= 96:
            if op == 27:
                reader.idx()
                vm += 4
            elif 96 <= op < 112:
                byte()
            while data[reader.p] != 22:
                expression()
            byte()
        elif op == 4:
            expression()
        else:
            raise ValueError(f"Unexpected bytecode token {op:#x} at {reader.p-1}; VM {vm}")

    while vm < size:
        expression()
    if (
        vm != size
        or reader.p != len(data) - 7
        or any(t not in boundaries for _, t in targets)
    ):
        raise ValueError("Invalid keyboard VM size or jump target")
    return size, targets, boundaries



def check_vm(data):
    size, targets, boundaries = scan_vm(data)
    return size, len(targets)



def verify_arena(original, modified):
    old, new = Package(original), Package(modified)
    count = 0
    for r in old.records():
        if not r['path'].startswith('menuStartArenaServer.') or r['class_name'] != 'Function':
            continue
        a, b = body(old, r['index']), body(new, r['index'])
        if r['path'].endswith('.UpdateValues'):
            if check_vm(a) != (406, 2) or check_vm(b) != (411, 2):
                raise ValueError('Unexpected arena display branches')
        elif a != b:
            raise ValueError('Arena input/save function changed')
        count += 1
    print(f'ARENA VM PASS: 406->411 VM bytes; 2 valid branches; {count-1} input/save functions unchanged')

def run(mode, reference, target, profile):
    original, current = Package(reference), Package(target)
    count = 0
    for spec in profile['display_expressions']:
        index = next(r['index'] for r in original.records() if r['path'] == spec['export'])
        target_index = next(r['index'] for r in current.records() if r['path'] == spec['export'])
        source = body(original, index)
        if digest(source) != spec['export_sha256']:
            raise ValueError('Unexpected reference function')
        expected = source if mode == 'baseline' else replace_casts(source, spec, current.names.index(spec['helper']))
        actual = body(current, target_index)
        if actual != expected:
            raise ValueError('Display function read-back differs')
        if script_header(actual)[2] != spec['script_size'] + (sum(e.get('vm_delta', 5) for e in spec['edits']) if mode == 'modified' else 0):
            raise ValueError('Unexpected VM size')
        count += len(spec['edits'])
    # Toggle/setter functions must remain original, even in a full localized build.
    checked = 0
    for rec in original.records():
        if rec['class_name'] != 'Function' or not rec['path'].startswith('menuOptions.'):
            continue
        if rec['path'] == 'menuOptions.DrawValues':
            continue
        index = next(r['index'] for r in current.records() if r['path'] == rec['path'])
        if body(original, rec['index']) != body(current, index):
            raise ValueError('Unrelated controls function changed: ' + rec['path'])
        checked += 1
    for spec in profile['display_expressions']:
        name = 'menuLong.' + spec['helper']
        i = next(r['index'] for r in original.records() if r['path'] == name)
        j = next(r['index'] for r in current.records() if r['path'] == name)
        if body(original, i) != body(current, j):
            raise ValueError('Existing locale helper changed')
    if mode == 'modified':
        verify_arena(reference, target)
    description = 'original value expressions retained' if mode == 'baseline' else 'localized existing helpers; guarded VM sizes verified'
    print(f'{mode.upper()} MENU PASS: {count} displays; {description}; '
          f'{checked} other controls functions unchanged; helper unchanged; no game launched')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=['baseline', 'modified'])
    parser.add_argument('--reference', type=Path, required=True)
    parser.add_argument('--package', type=Path, required=True)
    parser.add_argument('--profile', type=Path, default=Path('profiles/gog-v68.json'))
    args = parser.parse_args()
    run(args.mode, args.reference, args.package, json.loads(args.profile.read_text('utf8')))
