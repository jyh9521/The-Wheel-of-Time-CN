"""Prepare an isolated real-game FMV QA copy. Never launch or write the source game."""
import argparse
import json
import re
import shutil
from pathlib import Path

from src.patch.movie_player import patch, restore, sha
from tools.pack.movie_text_probe import build as build_movie

ROOT=Path(__file__).resolve().parents[2]
PROFILE=ROOT/'profiles/fmv-player.json'


def configure_1080p(data):
    encoding='utf-16' if data.startswith((b'\xff\xfe',b'\xfe\xff')) else 'cp1252'
    text=data.decode(encoding)
    if not re.search(r'(?mi)^Language=int\s*$',text):
        raise ValueError('Game QA requires the existing English language setting')
    policy=json.loads((ROOT/'profiles/qa-policy.json').read_text('utf8'))
    if policy['active_resolutions']!=[[1920,1080]]:
        raise ValueError('This experiment requires the established single 1080p QA policy')
    for key,value in dict(WindowedViewportX=1920,WindowedViewportY=1080,
                          FullscreenViewportX=1920,FullscreenViewportY=1080,StartupFullscreen='True').items():
        text,count=re.subn(r'(?m)^'+key+r'=[^\r\n]*',key+'='+str(value),text)
        if count!=1:
            raise ValueError('Missing/ambiguous viewport field: '+key)
    return text.encode(encoding)


def prepare(source,out,locale):
    source,out=source.resolve(),out.resolve()
    if out.exists() or out.is_relative_to(source) or source.is_relative_to(out):
        raise ValueError('Choose a new output directory outside the source game')
    if not re.fullmatch(r'[A-Za-z0-9-]+',locale):
        raise ValueError('Invalid locale')
    profile=json.loads(PROFILE.read_text('utf8'))
    dll=(source/profile['file']).read_bytes()
    modified,diff=patch(dll,profile)
    config=json.loads((ROOT/'locales'/locale/'fmv_probe.json').read_text('utf8'))
    movie_name=config['movie']
    if Path(movie_name).name!=movie_name:
        raise ValueError('Invalid movie basename')
    movie=(source/'Movies'/movie_name).read_bytes()
    changed_movie,movie_diff=build_movie(movie,config)
    settings=(source/'System/WoT.ini').read_bytes()
    configured=configure_1080p(settings)
    if not (source/'System/WoT.exe').is_file():
        raise ValueError('Game executable missing')
    out.mkdir(parents=True)
    files=[]
    for directory in ['System','Maps','Textures','Sounds','Music','Movies']:
        folder=source/directory
        if not folder.is_dir():
            raise ValueError('Required source directory missing: '+directory)
        for path in sorted(folder.rglob('*')):
            if not path.is_file() or path.suffix.lower() in {'.log','.tmp','.bak'}:
                continue
            relative=path.relative_to(source);dest=out/relative
            dest.parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(path,dest)  # physical copies, not links to immutable source resources
            fingerprint=sha(path.read_bytes())
            if sha(dest.read_bytes())!=fingerprint:
                raise ValueError('Copy changed: '+str(relative))
            files.append(dict(file=relative.as_posix(),size=dest.stat().st_size,sha256=fingerprint))
    (out/'Save').mkdir(exist_ok=True)
    baseline=out/'.fmv-baseline'
    baseline.mkdir()
    (baseline/'WinDrv.dll').write_bytes(dll)
    (baseline/movie_name).write_bytes(movie)
    (baseline/'WoT.ini').write_bytes(settings)
    (out/'MODIFIED_FILE.dll').write_bytes(modified)
    (out/'DIFF_FILE.json').write_text(json.dumps(diff,indent=2),'utf8')
    (out/'MOVIE_DIFF.json').write_text(json.dumps(movie_diff,indent=2),'utf8')
    (out/'System/WinDrv.dll').write_bytes(modified)
    (out/'Movies'/movie_name).write_bytes(changed_movie)
    (out/'System/WoT.ini').write_bytes(configured)
    manifest=dict(test_only=True,root=str(out),source=str(source),locale=locale,
                  dll_sha256=sha(modified),dll_baseline_sha256=sha(dll),movie=movie_name,
                  movie_sha256=sha(changed_movie),movie_baseline_sha256=sha(movie),
                  resolution=[1920,1080],language_unchanged='int',copied_files=files,
                  modified=['System/WinDrv.dll','Movies/'+movie_name,'System/WoT.ini'])
    (out/'TEST_MANIFEST.json').write_text(json.dumps(manifest,indent=2),'utf8')
    launcher='''$ErrorActionPreference = 'Stop'
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$m = Get-Content -LiteralPath (Join-Path $here 'TEST_MANIFEST.json') -Raw | ConvertFrom-Json
if ((Get-FileHash -LiteralPath (Join-Path $here 'System/WinDrv.dll')).Hash.ToLowerInvariant() -ne $m.dll_sha256) { throw 'Test DLL hash mismatch' }
if ((Get-FileHash -LiteralPath (Join-Path $here ('Movies/'+$m.movie))).Hash.ToLowerInvariant() -ne $m.movie_sha256) { throw 'Test movie hash mismatch' }
Push-Location (Join-Path $here 'System')
try { & .\\WoT.exe Entry } finally { Pop-Location }
'''
    (out/'LAUNCH_GAME.ps1').write_text(launcher,'utf8')
    script='''#!/usr/bin/env bash
set -euo pipefail
dir="$(cd "$(dirname "$0")" && pwd)"
cd "$(cygpath -u "{root}")"
python -m tools.build.build_fmv_game_probe restore-dll --input "$dir/MODIFIED_FILE.dll" --diff "$dir/DIFF_FILE.json" --output "${{1:?Supply NEW restored DLL copy path}}"
'''.format(root=str(ROOT).replace('\\','/'))
    (out/'ROLLBACK.sh').write_text(script,'utf8')
    if sha((source/profile['file']).read_bytes())!=sha(dll) or sha((source/'Movies'/movie_name).read_bytes())!=sha(movie) or (source/'System/WoT.ini').read_bytes()!=settings:
        raise ValueError('Source changed during preparation')
    print('GAME FMV PREPARE PASS: '+str(len(files))+' physical copies; 3 approved files changed; source unchanged; not launched')
    print('LAUNCHER: '+str(out/'LAUNCH_GAME.ps1'))


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('mode',choices=['build','inspect','restore-dll'])
    p.add_argument('--source',type=Path)
    p.add_argument('--out',type=Path,default=ROOT/'build/fmv-game-qa')
    p.add_argument('--locale',default='zh-CN')
    p.add_argument('--input',type=Path)
    p.add_argument('--output',type=Path)
    p.add_argument('--diff',type=Path)
    args=p.parse_args()
    if args.mode=='build':
        if not args.source:p.error('--source required')
        prepare(args.source,args.out,args.locale)
        return
    if not args.input or not args.diff:p.error('--input/--diff required')
    data=args.input.read_bytes();diff=json.loads(args.diff.read_text('utf8'))
    if args.mode=='restore-dll':
        if not args.output or args.output.exists() or args.output.resolve()==args.input.resolve():
            raise ValueError('Restore output must be a new copy')
        result=restore(data,diff);args.output.write_bytes(result)
        print('ROLLBACK PASS: '+sha(result));return
    identity=sha(data)
    if identity==diff['source_sha256']:
        print('BASELINE PASS: text indices=-3,-2,-1,0,1; original audio selector unchanged')
    elif identity==diff['output_sha256']:
        print('MODIFIED PASS: text indices=0,0,0,0,0; original audio selector unchanged')
    else:raise ValueError('Unknown DLL identity')


if __name__=='__main__':main()
