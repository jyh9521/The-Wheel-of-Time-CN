"""Read-back validation of profiled menu display expressions; no game launch."""
import argparse
import json
from pathlib import Path
from src.patch.display_expressions import digest, replace_casts, script_header
from tools.pack.ue1 import Package, body


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
        if script_header(actual)[2] != spec['script_size'] + (5 * len(spec['edits']) if mode == 'modified' else 0):
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
    description = 'raw bool casts retained' if mode == 'baseline' else 'localized GetOnOffStr calls; VM size 293 -> 323'
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
