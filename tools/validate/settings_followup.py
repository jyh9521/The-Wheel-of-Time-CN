"""Verify texture values, credits array and native layout, without launching WoT."""
import argparse
import json
import struct
from pathlib import Path
import pefile
from src.patch.credits import read_rows
from src.patch.display_expressions import replace_casts
from tools.pack.ue1 import Package, body


def verify(mode, game, resources, profile):
    original = Package(game / 'System/WOT.u')
    current = Package(resources / 'WOT.u')
    indices = {r['path']:r['index'] for r in current.records()}
    originals = {r['path']:r['index'] for r in original.records()}
    spec = profile['display_expressions'][1]
    expected = body(original, originals[spec['export']])
    if mode == 'modified':
        expected = replace_casts(expected, spec, current.names.index(spec['helper']))
    assert body(current, indices[spec['export']]) == expected
    credits = profile['credits']
    rows = read_rows(body(current, indices['Credits']), credits['defaults_offset'], current.names.index('CreditsText'))
    count = 206 if mode == 'modified' else 204
    assert len(rows) == count
    dim = struct.unpack_from('<i', body(current, indices['Credits.CreditsText']), credits['dimension_offset'])[0]
    assert dim == count
    expected_script = bytearray(body(original, originals['Credits.PostRender']))
    if mode == 'modified':
        for offset in credits['array_count_offsets']:
            expected_script[offset + 1] = 206
        assert rows[-1][1] == '简体中文补丁制作：伯翎飞云'
    assert body(current, indices['Credits.PostRender']) == expected_script
    # Entire hardware menu except the read-only display getter remains unchanged.
    protected = 0
    for rec in original.records():
        if rec['class_name'] == 'Function' and rec['path'].startswith('menuConfiguration.') and rec['path'] != spec['export']:
            assert body(current, indices[rec['path']]) == body(original, rec['index'])
            protected += 1
    dll = pefile.PE(str(resources / 'Window.dll'))
    metrics = profile['native_properties']
    height = struct.unpack_from('<i', dll.get_data(metrics['height_rvas'][0], 5), 1)[0]
    assert height == (32 if mode == 'modified' else 16)
    if mode == 'modified':
        assert dll.sections[-1].Name == b'.locale\0'
    else:
        assert all(s.Name != b'.locale\0' for s in dll.sections)
    print(f'{mode.upper()} SETTINGS PASS: texture display verified; {count} credits rows; array size/counts match; '
          f'{protected} hardware setter/other functions unchanged; native row height={height}; no game launched')


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('mode', choices=['baseline','modified'])
    p.add_argument('--game-dir', type=Path, required=True)
    p.add_argument('--resources', type=Path, required=True)
    p.add_argument('--profile', type=Path, default=Path('profiles/gog-v68.json'))
    args = p.parse_args()
    verify(args.mode, args.game_dir, args.resources, json.loads(args.profile.read_text('utf8')))
