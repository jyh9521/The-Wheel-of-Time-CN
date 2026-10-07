"""Compile a single-file portable WinForms installer with embedded verified deltas."""
import argparse
import base64
import json
from pathlib import Path
import subprocess
import sys
import zipfile
import zlib

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from src.patch.delta import create,sha,apply


def package(source,game,window,out,work):
    with zipfile.ZipFile(source) as archive:
        contents=json.loads(archive.read('LocalizationTest/CONTENTS.json'))
        if any(sha(archive.read(n))!=h for n,h in contents.items()):raise ValueError('Input package checksum differs')
        members={n:archive.read(n) for n in archive.namelist() if n.startswith('LocalizationTest/') and not n.endswith('CONTENTS.json')}
    manifest=json.loads(members['LocalizationTest/MANIFEST.json'])
    locale_dir=(ROOT/'locales'/manifest['locale']).resolve()
    if locale_dir.parent != (ROOT/'locales').resolve():raise ValueError('Invalid locale directory')
    members['LocalizationTest/UI.json']=(locale_dir/'installer-ui.json').read_bytes()
    path='System/Window.dll'
    original=(game/path).read_bytes();modified=window.read_bytes()
    delta=create(original,modified)
    if apply(original,delta)!=modified:raise ValueError('Wizard delta verification failed')
    ops=[]
    for op in delta['operations']:
        if 'copy' in op:ops.append(op)
        else:
            data=zlib.decompress(base64.b64decode(op['literal']));name='payload/'+sha(data)+'.bin'
            members['LocalizationTest/'+name]=data
            ops.append(dict(payload=name,sha256=sha(data),size=len(data)))
    entry=next(e for e in manifest['files'] if e['path']==path)
    if entry['original_sha256']!=sha(original):raise ValueError('Wizard original version differs')
    wizard_report=json.loads((window.parent.parent/'LAUNCHER_DIFF.json').read_text(encoding='utf-8'))
    if wizard_report['source_sha256']!=entry['modified_sha256'] or wizard_report['modified_sha256']!=sha(modified):raise ValueError('Wizard report identity differs')
    if not wizard_report['non_resource_sections_unchanged'] or not wizard_report['font_metrics_and_control_ids_unchanged']:raise ValueError('Wizard preservation validation missing')
    entry.update({k:v for k,v in delta.items() if k not in ('format','operations')});entry['operations']=ops
    members['LocalizationTest/MANIFEST.json']=json.dumps(manifest,ensure_ascii=False,indent=2).encode('utf-8')
    members['LocalizationTest/Manage-Patch.ps1']=(ROOT/'assets/templates/player-test.ps1').read_bytes()
    members['LocalizationTest/CONTENTS.json']=json.dumps({n:sha(b) for n,b in sorted(members.items())},indent=2).encode('utf-8')
    work.mkdir(parents=True,exist_ok=True);out.parent.mkdir(parents=True,exist_ok=True)
    payload=work/'Package.zip'
    with zipfile.ZipFile(payload,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as archive:
        for name,data in sorted(members.items()):
            info=zipfile.ZipInfo(name,(2020,1,1,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;archive.writestr(info,data)
    with zipfile.ZipFile(payload) as archive:
        if archive.testzip():raise ValueError('Payload CRC failed')
        for name,data in members.items():
            if archive.read(name)!=data:raise ValueError('Payload readback differs')
    csc=Path(r'C:\Windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe')
    if not csc.exists():raise ValueError('.NET Framework C# compiler missing')
    cmd=[str(csc),'/nologo','/utf8output','/target:winexe','/platform:anycpu','/optimize+',
         '/reference:System.Windows.Forms.dll','/reference:System.Drawing.dll',
         '/reference:System.IO.Compression.dll','/reference:System.IO.Compression.FileSystem.dll',
         '/reference:System.Web.Extensions.dll',
         '/out:'+str(out.resolve()),'/resource:'+str(payload.resolve())+',Package.zip',str(ROOT/'src/installer/PortableInstaller.cs')]
    result=subprocess.run(cmd,capture_output=True,text=True)
    (work/'COMPILER.txt').write_text(result.stdout+result.stderr,encoding='utf-8')
    if result.returncode:raise ValueError(result.stdout+result.stderr)
    out.with_suffix('.exe.sha256').write_text(sha(out.read_bytes())+'  '+out.name+'\n',encoding='ascii')
    (work/'DIFF_FILE.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
    print(f'PORTABLE INSTALLER BUILD PASS: bytes={out.stat().st_size}; resources={len(manifest["files"])}; embedded deltas; no proprietary full files')
    return manifest


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('source-package','game-dir','window','out','work'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();package(a.source_package,a.game_dir,a.window,a.out,a.work)
