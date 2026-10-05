"""Build and install native FMV captions into a NEW localized game copy."""
from tools.build.launcher import portable_launcher

import argparse
import json
import os
import re
import shutil
from pathlib import Path

from tools.pack.movie_text import rebuild, read_translations, text_tables
from tools.pack.movie_text_probe import sha, restore as restore_movie
from src.patch.movie_player import patch, restore as restore_dll
from tools.build.build_fmv_game_probe import configure_1080p

ROOT=Path(__file__).resolve().parents[2]


def load(path):return json.loads(path.read_text('utf8'))
def save(path,value):path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n','utf8')


def audit(folder,locale,mode):
    profile=load(ROOT/'profiles/fmv-movies.json');data_dir=ROOT/'locales'/locale/'fmv'
    config=load(data_dir/'config.json');count=0;movies=0
    from tools.pack.movie_text import wrap
    for p in profile['movies']:
        data=(folder/p['movie']).read_bytes()
        if mode=='baseline':
            if len(data)!=p['size'] or sha(data)!=p['sha256']:raise ValueError('Baseline identity mismatch: '+p['movie'])
        if p['track_id'] is None:continue
        t=text_tables(data,p['track_id']);translations=read_translations(data_dir/(Path(p['movie']).stem+'.tsv'))
        if len(t['samples'])!=len(p['samples']):raise ValueError('Sample count changed')
        for s,known in zip(t['samples'],p['samples']):
            if mode=='baseline' and s['sha256']!=known['sha256']:raise ValueError('Baseline sample changed')
            if mode=='modified':
                expected=wrap(translations[s['index']],config['line_units']) if known['nonempty'] else ''
                if s['text']!=expected:raise ValueError('Caption mismatch: '+p['movie'])
            if s['begin']!=known['begin'] or s['duration']!=known['duration']:raise ValueError('Clock changed')
        count+=len(translations);movies+=1
    print(mode.upper()+' PASS: '+str(movies)+' text-track movies; '+str(count)+' translated cues; '+str(len(profile['movies']))+' movie identities/timelines checked')


def build(game,runtime,out,locale,resource_build=None):
    game,runtime,out=game.resolve(),runtime.resolve(),out.resolve()
    if not re.fullmatch('[A-Za-z0-9-]+',locale):raise ValueError('Invalid locale')
    if out.exists() or any(out.is_relative_to(s) or s.is_relative_to(out) for s in (game,runtime)):
        raise ValueError('Choose a NEW destination outside source games')
    profile=load(ROOT/'profiles/fmv-movies.json');lang=ROOT/'locales'/locale/'fmv';config=load(lang/'config.json')
    audit(game/'Movies',locale,'baseline')
    # Preflight translations and all version constraints before creating the game copy.
    for p in profile['movies']:
        source=(game/'Movies'/p['movie']).read_bytes()
        if sha((runtime/'Movies'/p['movie']).read_bytes())!=p['sha256']:
            raise ValueError('Runtime movie is not baseline: '+p['movie'])
        if p['track_id'] is not None:rebuild(source,p,read_translations(lang/(Path(p['movie']).stem+'.tsv')),config)
    dll=(runtime/'System/WinDrv.dll').read_bytes();new_dll,dll_diff=patch(dll,load(ROOT/'profiles/fmv-player.json'))
    resource_hashes={}
    if resource_build:
        from src.patch.delta import apply
        bundle=load(resource_build/'PATCH.json')
        from install import targets
        targets(runtime,bundle)
        for name,delta in bundle['files'].items():
            if name in ('System/WinDrv.dll','System/WoT.ini'):raise ValueError('Resource bundle overlaps FMV transaction')
            result=apply((runtime/name).read_bytes(),delta)
            if result!=(resource_build/'resources'/name).read_bytes():raise ValueError('Resource build identity mismatch')
            resource_hashes[name]=sha(result)
    settings=(runtime/'System/WoT.ini').read_bytes();new_settings=configure_1080p(settings)
    if not (runtime/'System/WoT.exe').is_file():raise ValueError('Runtime executable missing')
    out.mkdir(parents=True);(out/'Save').mkdir();(out/'diffs').mkdir();source_files=[]
    for directory in ('System','Maps','Textures','Sounds','Music','Movies'):
        if not (runtime/directory).is_dir():raise ValueError('Runtime directory missing')
        for path in sorted((runtime/directory).rglob('*')):
            if not path.is_file() or path.suffix.lower() in {'.log','.tmp','.bak'}:continue
            rel=path.relative_to(runtime);dest=out/rel;dest.parent.mkdir(parents=True,exist_ok=True)
            digest=sha(path.read_bytes());shutil.copy2(path,dest)
            if sha(dest.read_bytes())!=digest:raise ValueError('Physical copy changed')
            source_files.append(dict(file=rel.as_posix(),sha256=digest))
    if resource_build:
        from install import transaction
        transaction('apply',resource_build/'PATCH.json',out)
        transaction('verify',resource_build/'PATCH.json',out)
    (out/'System/WinDrv.dll').write_bytes(new_dll);save(out/'diffs/WinDrv.json',dll_diff)
    (out/'System/WoT.ini').write_bytes(new_settings)
    (out/'diffs/WoT.ini.original').write_bytes(settings)
    modified=['System/WinDrv.dll','System/WoT.ini'];movies=[]
    for p in profile['movies']:
        if p['track_id'] is None:continue
        original=(game/'Movies'/p['movie']).read_bytes()
        data,diff=rebuild(original,p,read_translations(lang/(Path(p['movie']).stem+'.tsv')),config)
        (out/'Movies'/p['movie']).write_bytes(data);save(out/'diffs'/(p['movie']+'.json'),diff)
        movies.append(dict(movie=p['movie'],sha256=sha(data),translated=diff['translated']))
        modified.append('Movies/'+p['movie'])
    manifest=dict(locale=locale,original_game=str(game),runtime_source=str(runtime),movies=movies,
                  modified=modified,source_files=source_files,localized_resources=resource_hashes,
                  dll_sha256=sha(new_dll),settings_sha256=sha(new_settings),
                  resolution=[1920,1080],audio_video_transcoded=False)
    manifest['translation_inputs']={p.name:sha(p.read_bytes()) for p in sorted(lang.glob('*')) if p.is_file()}
    manifest['movie_profile_sha256']=sha((ROOT/'profiles/fmv-movies.json').read_bytes())
    manifest['glossary_sha256']=sha((ROOT/config['reference']).read_bytes())
    save(out/'DIFF_FILE.json',manifest)
    shutil.copy2(out/'Movies/Intro.mov',out/'MODIFIED_FILE.mov')
    manifest['MODIFIED_FILE']=str(out/'MODIFIED_FILE.mov');save(out/'DIFF_FILE.json',manifest)
    launcher='''$ErrorActionPreference = 'Stop'
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$m = Get-Content -LiteralPath (Join-Path $here 'DIFF_FILE.json') -Raw | ConvertFrom-Json
foreach ($movie in $m.movies) {
 if ((Get-FileHash -LiteralPath (Join-Path $here ('Movies/'+$movie.movie))).Hash.ToLowerInvariant() -ne $movie.sha256) { throw ('Movie hash mismatch: '+$movie.movie) }
}
if ((Get-FileHash -LiteralPath (Join-Path $here 'System/WinDrv.dll')).Hash.ToLowerInvariant() -ne $m.dll_sha256) { throw 'FMV player hash mismatch' }
Push-Location (Join-Path $here 'System')
try { & .\\WoT.exe } finally { Pop-Location }
'''
    launcher=portable_launcher(launcher)
    (out/'LAUNCH_GAME.ps1').write_text(launcher,'utf8')
    rollback='''#!/usr/bin/env bash
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
cd "$(cygpath -u "{root}")"
python -m tools.build.build_fmv rollback --input "$here" --out "${{1:?Supply a NEW rollback-copy directory}}"
'''.format(root=str(ROOT).replace('\\','/'))
    (out/'ROLLBACK.sh').write_text(rollback,'utf8');os.chmod(out/'ROLLBACK.sh',0o755)
    verify(out,locale)
    for row in source_files:
        if sha((runtime/row['file']).read_bytes())!=row['sha256']:raise ValueError('Source runtime changed')
    audit(game/'Movies',locale,'baseline')
    print('BUILD PASS: '+str(len(movies))+' movies / '+str(sum(m['translated'] for m in movies))+' cues installed into new 1080p game copy; media payloads and source games unchanged; game not launched')


def verify(folder,locale):
    manifest=load(folder/'DIFF_FILE.json');count=0
    for p in manifest['movies']:
        data=(folder/'Movies'/p['movie']).read_bytes();diff=load(folder/'diffs'/(p['movie']+'.json'))
        if sha(data)!=p['sha256']:raise ValueError('Installed movie identity mismatch')
        original=restore_movie(data,diff)
        if sha(original)!=sha((Path(manifest['original_game'])/'Movies'/p['movie']).read_bytes()):
            raise ValueError('Media preservation/rollback mismatch')
        count+=1
    data=(folder/'System/WinDrv.dll').read_bytes()
    if sha(data)!=manifest['dll_sha256']:raise ValueError('Installed DLL identity mismatch')
    restore_dll(data,load(folder/'diffs/WinDrv.json'))
    if (folder/'MODIFIED_FILE.mov').read_bytes()!=(folder/'Movies/Intro.mov').read_bytes():
        raise ValueError('Representative movie differs from installed intro')
    if sha((folder/'System/WoT.ini').read_bytes())!=manifest['settings_sha256']:raise ValueError('QA viewport changed')
    for row in manifest['source_files']:
        expected=manifest.get('localized_resources',{}).get(row['file'],row['sha256'])
        if row['file'] not in manifest['modified'] and sha((folder/row['file']).read_bytes())!=expected:
            raise ValueError('Unrelated installed file changed: '+row['file'])
    audit(folder/'Movies',locale,'modified')
    print('VERIFY PASS: '+str(count)+' movie rollback hashes; selector/audio path preserved; unrelated resources unchanged')


def rollback(folder,out):
    folder,out=folder.resolve(),out.resolve()
    if out.exists() or out.is_relative_to(folder) or folder.is_relative_to(out):raise ValueError('Rollback destination must be a NEW separate copy')
    m=load(folder/'DIFF_FILE.json');verify(folder,m['locale']);out.mkdir(parents=True);(out/'Movies').mkdir();(out/'System').mkdir()
    for row in m['source_files']:
        if row['file'] not in m['modified']:continue
        if row['file'].startswith('Movies/'):
            name=Path(row['file']).name;data=restore_movie((folder/row['file']).read_bytes(),load(folder/'diffs'/(name+'.json')))
        elif row['file']=='System/WinDrv.dll':data=restore_dll((folder/row['file']).read_bytes(),load(folder/'diffs/WinDrv.json'))
        else:data=(folder/'diffs/WoT.ini.original').read_bytes()
        (out/row['file']).write_bytes(data)
        if sha((out/row['file']).read_bytes())!=row['sha256']:raise ValueError('Restored copy identity mismatch')
    print('ROLLBACK PASS: '+str(len(m['movies']))+' original movies, WinDrv.dll and WoT.ini restored byte-for-byte on separate copy; installed game remains localized')


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('mode',choices=['build','verify','rollback','audit'])
    p.add_argument('--game-dir',type=Path);p.add_argument('--runtime-dir',type=Path)
    p.add_argument('--resource-build',type=Path,help='Fresh ordinary localization build; runtime-dir may then be the original game')
    p.add_argument('--input',type=Path);p.add_argument('--out',type=Path);p.add_argument('--locale',default='zh-CN')
    p.add_argument('--state',choices=['baseline','modified'],default='baseline');a=p.parse_args()
    if not re.fullmatch('[A-Za-z0-9-]+',a.locale):raise ValueError('Invalid locale')
    if a.mode=='build':
        if not all((a.game_dir,a.runtime_dir,a.out)):p.error('build requires --game-dir --runtime-dir --out')
        build(a.game_dir,a.runtime_dir,a.out,a.locale,a.resource_build)
    elif a.mode=='audit':
        if not a.input:p.error('--input required')
        audit(a.input,a.locale,a.state)
    elif a.mode=='verify':
        if not a.input:p.error('--input required')
        verify(a.input,a.locale)
    else:
        if not a.input or not a.out:p.error('rollback requires --input --out')
        rollback(a.input,a.out)


if __name__=='__main__':main()
