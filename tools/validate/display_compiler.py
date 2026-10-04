"""Compile our minimal bool-display proof using the user's verified GOG UCC."""
import argparse
import json
import shutil
import subprocess
from pathlib import Path
from src.patch.display_expressions import digest, script_header
from tools.build.pipeline import check_originals
from tools.pack.ue1 import Package, body

ROOT = Path(__file__).resolve().parents[2]


def run(game, out):
    game, out = game.resolve(), out.resolve()
    if out.is_relative_to(game) or game.is_relative_to(out):
        raise ValueError('Use a compiler output independent of the game directory')
    check_originals(game, json.loads((ROOT / 'profiles/gog-v68.json').read_text('utf8')))
    for expected in json.loads((ROOT / 'profiles/subtitle-runtime.json').read_text('utf8'))['compiler_inputs']:
        data = (game / expected['file']).read_bytes()
        if len(data) != expected['size'] or digest(data) != expected['sha256']:
            raise ValueError('Unsupported compiler input: ' + expected['file'])
    system = out / 'compiler/System'
    system.mkdir(parents=True, exist_ok=True)
    for source in (game / 'System').iterdir():
        if source.suffix.lower() in ('.dll', '.int') or source.name in ('UCC.exe', 'Default.ini', 'DefUser.ini'):
            shutil.copyfile(source, system / source.name)
    source = out / 'compiler/LocaleDisplayProbe/Classes/LocaleDisplayProbe.uc'
    source.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(ROOT / 'tests/fixtures/LocaleDisplayProbe.uc', source)
    ini = '[Core.System]\nPaths=' + str(system / '*.u') + '\n'
    ini += ''.join('Paths=' + str(game / folder / pattern) + '\n' for folder, pattern in
                   [('System', '*.u'), ('Textures', '*.utx'), ('Sounds', '*.uax'), ('Music', '*.umx'), ('Maps', '*.wot')])
    ini += '\n[Engine.Engine]\nEditorEngine=Editor.EditorEngine\nLanguage=int\n[Editor.EditorEngine]\n'
    ini += ''.join('EditPackages=' + name + '\n' for name in
                   ['Core', 'Engine', 'Legend', 'WOT', 'Angreal', 'WOTPawns', 'LocaleDisplayProbe'])
    (system / 'WoT.ini').write_text(ini, 'ascii')
    binary = system / 'LocaleDisplayProbe.u'
    if binary.exists():
        binary.unlink()  # Only our owned probe package; UCC otherwise skips it.
    result = subprocess.run([str(system / 'UCC.exe'), 'Editor.MakeCommandlet', '-ini=WoT.ini'],
                            cwd=system, capture_output=True, text=True, encoding='cp1252')
    (out / 'COMPILER.txt').write_text(result.stdout + result.stderr, 'utf8')
    if result.returncode or 'Success - 0 error(s), 0 warnings' not in result.stdout:
        raise ValueError('Probe compiler failed; see COMPILER.txt')
    package = Package(binary)
    scripts = {}
    for record in package.records():
        if record['class_name'] == 'Function':
            data = body(package, record['index'])
            _, start, size = script_header(data)
            scripts[record['path']] = dict(vm_size=size, script_hex=data[start:-7].hex())
    raw, mapped = scripts['LocaleDisplayProbe.Raw'], scripts['LocaleDisplayProbe.Mapped']
    if raw['vm_size'] != 10 or mapped['vm_size'] != 15:
        raise ValueError('Unexpected VM script size delta')
    if scripts['LocaleDisplayProbe.DetailMapped']['vm_size'] != 48:
        raise ValueError('Unexpected texture-detail expression VM size')
    # Compact names are one byte in this tiny package; the VM uses four bytes.
    helper = package.names.index('GetOnOffStr')
    from tools.pack.ue1 import ci
    raw_code = bytes.fromhex(raw['script_hex'])
    mapped_code = bytes.fromhex(mapped['script_hex'])
    if mapped_code != raw_code[:1] + b'\x1b' + ci(helper) + raw_code[2:-2] + b'\x16' + raw_code[-2:]:
        raise ValueError('Unexpected virtual-call serialization')
    (out / 'COMPILER_PROOF.json').write_text(json.dumps(scripts, indent=2) + '\n', 'utf8')
    print('COMPILER PROOF PASS: 0 errors; 0 warnings; bool cast VM=10; locale helper VM=15; delta=5; operand unchanged')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--game-dir', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    run(args.game_dir, args.out)
