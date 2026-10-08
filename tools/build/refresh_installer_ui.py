"""Recompile an installer UI without changing its verified resource manifest."""
import argparse
import base64
import difflib
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import zipfile
import zlib

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from src.patch.delta import apply


def merge_resources(members, bundle, game):
    """Replace rebuilt resources while preserving verified movie/native additions."""
    spec = json.loads(members['LocalizationTest/MANIFEST.json'])
    if bundle['locale'] != spec['locale']:
        raise ValueError('Resource locale differs')
    replacements = {}
    previous = {entry['path']: entry for entry in spec['files']}
    for path, delta in bundle['files'].items():
        relative = Path(path)
        if relative.is_absolute() or '..' in relative.parts or ':' in path or '\\' in path:
            raise ValueError('Invalid resource path')
        if path not in previous:
            raise ValueError('Resource not present in baseline manifest: ' + path)
        owned = path in bundle.get('owned_additions', [])
        old = previous[path]
        if owned != old['owned'] or delta['original_sha256'] != old['original_sha256']:
            raise ValueError('Resource baseline identity differs: ' + path)
        original = b'' if owned else (game / path).read_bytes()
        modified = apply(original, delta)
        operations = []
        for op in delta['operations']:
            if 'copy' in op:
                operations.append(dict(op))
            else:
                data = zlib.decompress(base64.b64decode(op['literal'], validate=True))
                if len(data) != op['size']:
                    raise ValueError('Resource literal length differs')
                digest = hashlib.sha256(data).hexdigest()
                name = 'payload/' + digest + '.bin'
                members['LocalizationTest/' + name] = data
                operations.append(dict(payload=name, sha256=digest, size=len(data)))
        replacements[path] = dict(path=path, owned=owned, operations=operations,
            **{k: v for k, v in delta.items() if k not in ('format', 'operations')})
        if hashlib.sha256(modified).hexdigest() != replacements[path]['modified_sha256']:
            raise ValueError('Resource output identity differs')
    spec['files'] = [replacements.get(entry['path'], entry) for entry in spec['files']]
    members['LocalizationTest/MANIFEST.json'] = json.dumps(spec, ensure_ascii=False, indent=2).encode('utf8')
    # Keep only literals used by the new manifest, not obsolete translation payloads.
    used = {'LocalizationTest/' + op['payload'] for entry in spec['files']
            for op in entry['operations'] if 'payload' in op}
    for name in list(members):
        if name.startswith('LocalizationTest/payload/') and name not in used:
            del members[name]


def refresh(payload, baseline, output, work, resources=None, game=None, baseline_resources=None, restore_payloads=()):
    work.mkdir(parents=True, exist_ok=True)
    shutil.copy2(baseline, work / 'BASELINE.exe')
    with zipfile.ZipFile(payload) as archive:
        if archive.testzip():
            raise ValueError('Baseline payload CRC differs')
        members = {name: archive.read(name) for name in archive.namelist()}
    checks = json.loads(members['LocalizationTest/CONTENTS.json'])
    for name, digest in checks.items():
        if hashlib.sha256(members[name]).hexdigest() != digest:
            raise ValueError('Baseline payload checksum differs: ' + name)
    old_manifest = members['LocalizationTest/MANIFEST.json']
    recoveries = json.loads(members.get('LocalizationTest/RESTORE_MANIFESTS.json', b'{}'))
    recoveries[hashlib.sha256(old_manifest).hexdigest()] = json.loads(old_manifest)
    for previous_payload in restore_payloads:
        with zipfile.ZipFile(previous_payload) as previous:
            identities = json.loads(previous.read('LocalizationTest/CONTENTS.json'))
            if previous.testzip() or any(hashlib.sha256(previous.read(n)).hexdigest() != h for n,h in identities.items()):
                raise ValueError('Recovery payload checksum differs')
            data = previous.read('LocalizationTest/MANIFEST.json')
            old_spec = json.loads(data)
            if old_spec['locale'] != json.loads(old_manifest)['locale']:
                raise ValueError('Recovery locale differs')
            recoveries[hashlib.sha256(data).hexdigest()] = old_spec
    if resources is not None:
        if game is None:
            raise ValueError('Original game directory required for refreshed resources')
        bundle = json.loads((resources / 'PATCH.json').read_text('utf8'))
        if baseline_resources is not None:
            previous = json.loads((baseline_resources / 'PATCH.json').read_text('utf8'))
            if previous['locale'] != bundle['locale'] or set(previous['files']) != set(bundle['files']):
                raise ValueError('Baseline resource set differs')
            bundle['files'] = {path: delta for path, delta in bundle['files'].items()
                if delta['modified_sha256'] != previous['files'][path]['modified_sha256']}
        merge_resources(members, bundle, game)
    spec = json.loads(members['LocalizationTest/MANIFEST.json'])
    spec['progress'] = {'directories': ['Save']}
    manifest = json.dumps(spec, ensure_ascii=False, indent=2).encode('utf8')
    members['LocalizationTest/MANIFEST.json'] = manifest
    members['LocalizationTest/RESTORE_MANIFESTS.json'] = json.dumps(recoveries, ensure_ascii=False, indent=2).encode('utf8')
    members['LocalizationTest/Manage-Patch.ps1'] = (ROOT / 'assets/templates/player-test.ps1').read_bytes()
    locale = json.loads(manifest)['locale']
    old_ui = members['LocalizationTest/UI.json']
    new_ui = (ROOT / 'locales' / locale / 'installer-ui.json').read_bytes()
    members['LocalizationTest/UI.json'] = new_ui
    members['LocalizationTest/CONTENTS.json'] = json.dumps({
        name: hashlib.sha256(data).hexdigest() for name, data in members.items()
        if name != 'LocalizationTest/CONTENTS.json'
    }, indent=2).encode('ascii')
    package = work / 'Package.zip'
    with zipfile.ZipFile(package, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name, data in sorted(members.items()):
            archive.writestr(name, data)
    with zipfile.ZipFile(package) as archive:
        if archive.testzip() or archive.read('LocalizationTest/MANIFEST.json') != manifest:
            raise ValueError('Payload readback differs')
    command = [r'C:\Windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe',
        '/nologo', '/utf8output', '/target:winexe', '/platform:anycpu', '/optimize+',
        '/reference:System.Windows.Forms.dll', '/reference:System.Drawing.dll',
        '/reference:System.IO.Compression.dll', '/reference:System.IO.Compression.FileSystem.dll',
        '/reference:System.Web.Extensions.dll', '/out:' + str(output.resolve()),
        '/resource:' + str(package.resolve()) + ',Package.zip',
        str(ROOT / 'src/installer/PortableInstaller.cs')]
    branding = ROOT / 'assets/installer'
    if (branding / 'logo.png').exists(): command.insert(-1, '/resource:' + str((branding / 'logo.png').resolve()) + ',InstallerLogo.png')
    if (branding / 'installer.ico').exists(): command.insert(-1, '/win32icon:' + str((branding / 'installer.ico').resolve()))
    result = subprocess.run(command, capture_output=True)
    (work / 'COMPILER.txt').write_bytes(result.stdout + result.stderr)
    if result.returncode:
        raise ValueError(result.stdout.decode('utf8', errors='replace'))
    digest = hashlib.sha256(output.read_bytes()).hexdigest()
    output.with_suffix('.exe.sha256').write_text(digest + '  ' + output.name + '\n', encoding='ascii')
    (work / 'DIFF_FILE.txt').write_text(''.join(difflib.unified_diff(
        old_ui.decode('utf8').splitlines(True), new_ui.decode('utf8').splitlines(True),
        fromfile='baseline/UI.json', tofile='modified/UI.json')), encoding='utf8')
    (work / 'DIFF_FILE.json').write_bytes(manifest)
    (work / 'MANIFEST.baseline.json').write_bytes(old_manifest)
    (work / 'ROLLBACK.sh').write_text('#!/usr/bin/env bash\nset -euo pipefail\ncp "' +
        (work / 'BASELINE.exe').resolve().as_posix() + '" "$1"\n', encoding='utf8')
    print('INSTALLER REFRESH PASS: verified payload and recovery manifests; SHA-256=' + digest)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('payload', 'baseline', 'output', 'work'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--resources', type=Path)
    parser.add_argument('--game-dir', type=Path)
    parser.add_argument('--baseline-resources', type=Path)
    parser.add_argument('--restore-payload', type=Path, action='append', default=[])
    args = parser.parse_args()
    refresh(args.payload, args.baseline, args.output, args.work, args.resources, args.game_dir, args.baseline_resources, args.restore_payload)
