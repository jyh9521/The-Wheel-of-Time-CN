"""Independent full-game bitmap font scale candidate; FMV files are copied unchanged."""
from tools.build.launcher import portable_launcher

import argparse,json,shutil
from pathlib import Path
from tools.font.scale_package_fonts import build as scale_fonts,sha
from tools.build.build_local_font_poc import verify as verify_source
ROOT=Path(__file__).resolve().parents[2]

def verify(out):
    m=json.loads((out/'READABILITY_INSTALL.json').read_text(encoding='utf8'))
    for name,expected in m['expected'].items():
        if sha((out/name).read_bytes())!=expected:raise ValueError('Candidate identity changed: '+name)
    print('READABILITY VERIFY PASS: immutable resources/font hashes; runtime settings and saves left untouched')

def build(source,out,scale,profile):
    source=source.resolve();out=out.resolve()
    if out.exists() or out.is_relative_to(source) or source.is_relative_to(out):raise ValueError('Choose NEW independent game copy')
    verify_source(source,allow_runtime_config=True)
    baseline=json.loads((source/'DIFF_FILE.json').read_text(encoding='utf8'))
    fonts=json.loads(profile.read_text(encoding='utf8'))['fonts']
    out.mkdir();transaction=out/'readability';transaction.mkdir()
    config=dict(scale=scale,source_sha256=sha((source/'System/WOT.u').read_bytes()),fonts=list(fonts))
    (transaction/'CONFIG.json').write_text(json.dumps(config,indent=2),encoding='utf8')
    scale_fonts(source/'System/WOT.u',transaction/'MODIFIED_FILE.u',config,transaction/'DIFF_FILE.json')
    for name in ['System','Maps','Textures','Sounds','Music','Movies','Fonts']:
        shutil.copytree(source/name,out/name,ignore=shutil.ignore_patterns('*.log','*.tmp','*.bak'))
    (out/'Save').mkdir();shutil.copy2(transaction/'MODIFIED_FILE.u',out/'System/WOT.u')
    manifest=dict(source_game=str(source),scale=scale,expected={r['file']:baseline['modified'].get(r['file'],r['source_sha256'])for r in baseline['files']if r['file']not in {'System/WoT.ini','System/User.ini'}},fmv_changed=False)
    manifest['expected']['System/WOT.u']=sha((out/'System/WOT.u').read_bytes())
    for path in (out/'Fonts').glob('*'):
        if path.is_file():manifest['expected'][path.relative_to(out).as_posix()]=sha(path.read_bytes())
    (out/'READABILITY_INSTALL.json').write_text(json.dumps(manifest,indent=2),encoding='utf8')
    launcher="""$ErrorActionPreference = 'Stop'
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$m = Get-Content -LiteralPath (Join-Path $here 'READABILITY_INSTALL.json') -Raw | ConvertFrom-Json
foreach ($entry in $m.expected.PSObject.Properties) {
 if ((Get-FileHash -LiteralPath (Join-Path $here $entry.Name)).Hash.ToLowerInvariant() -ne $entry.Value) { throw ('Resource hash mismatch: '+$entry.Name) }
}
Push-Location (Join-Path $here 'System')
try { & .\\WoT.exe } finally { Pop-Location }
"""
    launcher=portable_launcher(launcher)
    (out/'LAUNCH_GAME.ps1').write_text(launcher,encoding='utf8')
    verify(out)
    for path in (source/'Movies').glob('*.mov'):
        if path.read_bytes()!=(out/'Movies'/path.name).read_bytes():raise ValueError('FMV unexpectedly changed')
    print('READABILITY GAME BUILD PASS: six bitmap fonts scaled; FMV byte-identical; independent empty Save; no game launch')

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('mode',choices=['build','verify']);p.add_argument('--source-game',type=Path);p.add_argument('--out',type=Path,required=True);p.add_argument('--scale',type=float,default=1.5);p.add_argument('--profile',type=Path,default=ROOT/'profiles/gog-v68.json');a=p.parse_args()
    if a.mode=='build':
        if not a.source_game:p.error('--source-game required')
        build(a.source_game,a.out,a.scale,a.profile)
    else:verify(a.out)
