"""Recompile an installer UI without changing its verified resource manifest."""
import argparse
import difflib
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parents[2]


def refresh(payload, baseline, output, work):
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
    manifest = members['LocalizationTest/MANIFEST.json']
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
    result = subprocess.run(command, capture_output=True)
    (work / 'COMPILER.txt').write_bytes(result.stdout + result.stderr)
    if result.returncode:
        raise ValueError(result.stdout.decode('utf8', errors='replace'))
    digest = hashlib.sha256(output.read_bytes()).hexdigest()
    output.with_suffix('.exe.sha256').write_text(digest + '  ' + output.name + '\n', encoding='ascii')
    (work / 'DIFF_FILE.txt').write_text(''.join(difflib.unified_diff(
        old_ui.decode('utf8').splitlines(True), new_ui.decode('utf8').splitlines(True),
        fromfile='baseline/UI.json', tofile='modified/UI.json')), encoding='utf8')
    (work / 'ROLLBACK.sh').write_text('#!/usr/bin/env bash\nset -euo pipefail\ncp "' +
        (work / 'BASELINE.exe').resolve().as_posix() + '" "$1"\n', encoding='utf8')
    print('UI REFRESH PASS: resource manifest unchanged; SHA-256=' + digest)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('payload', 'baseline', 'output', 'work'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    refresh(args.payload, args.baseline, args.output, args.work)
