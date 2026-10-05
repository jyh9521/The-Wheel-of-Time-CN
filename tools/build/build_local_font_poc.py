"""Build a separate full-game local-font experiment; never alter formal/source games."""
from tools.build.launcher import portable_launcher

import argparse,json,os,shutil,re
from pathlib import Path
from tools.pack.movie_text import rebuild,read_translations,text_tables,wrap
from tools.pack.movie_text_probe import sha,restore as restore_movie
from tools.build.build_fmv import verify as verify_formal,load,save
from src.patch.local_font_loader import patch,restore as restore_dll

ROOT=Path(__file__).resolve().parents[2]


def build(source,original,font,config,out,locale):
    if not re.fullmatch('[A-Za-z0-9-]+',locale):raise ValueError('Invalid locale')
    source,original,out=source.resolve(),original.resolve(),out.resolve()
    if out.exists() or any(out.is_relative_to(s) or s.is_relative_to(out) for s in [source,original]):
        raise ValueError('Choose a NEW output outside both game inputs')
    verify_formal(source,locale)
    cfg=load(config);fm=load(font.with_suffix('.json'))
    if cfg['font']!=fm['family'] or sha(font.read_bytes())!=fm['font_sha256']:
        raise ValueError('Subset family/hash differs from config')
    if fm['translation_inputs']!={p.name:sha(p.read_bytes())for p in sorted((ROOT/'locales'/locale/'fmv').glob('*.tsv'))}:
        raise ValueError('Subset is stale relative to translations')
    dll,diff=patch((original/'System/WinDrv.dll').read_bytes(),load(ROOT/'profiles/fmv-player.json'),'Fonts/'+font.name)
    profile=load(ROOT/'profiles/fmv-movies.json');generated={};deltas={}
    for p in profile['movies']:
        data=(original/'Movies'/p['movie']).read_bytes()
        if len(data)!=p['size'] or sha(data)!=p['sha256']:raise ValueError('Unknown original movie')
        if p['track_id'] is not None:
            generated[p['movie']],deltas[p['movie']]=rebuild(data,p,read_translations(ROOT/'locales'/locale/'fmv'/(Path(p['movie']).stem+'.tsv')),cfg)
    out.mkdir();(out/'Save').mkdir();(out/'diffs').mkdir();(out/'Fonts').mkdir();files=[]
    for directory in ['System','Maps','Textures','Sounds','Music','Movies']:
        for path in sorted((source/directory).rglob('*')):
            if not path.is_file() or path.suffix.lower() in {'.log','.tmp','.bak'}:continue
            rel=path.relative_to(source);dest=out/rel;dest.parent.mkdir(parents=True,exist_ok=True)
            digest=sha(path.read_bytes());shutil.copy2(path,dest)
            if sha(dest.read_bytes())!=digest:raise ValueError('Copy failed')
            files.append(dict(file=rel.as_posix(),source_sha256=digest))
    modified={}
    for name,data in generated.items():
        (out/'Movies'/name).write_bytes(data);save(out/'diffs'/(name+'.json'),deltas[name]);modified['Movies/'+name]=sha(data)
    (out/'System/WinDrv.dll').write_bytes(dll);save(out/'diffs/local-font-loader.json',diff);modified['System/WinDrv.dll']=sha(dll)
    shutil.copy2(font,out/'Fonts'/font.name);shutil.copy2(font.with_name('OFL.txt'),out/'Fonts/OFL.txt')
    shutil.copy2(font.with_suffix('.json'),out/'Fonts/font-manifest.json')
    (out/'MODIFIED_FILE.dll').write_bytes(dll)
    m=dict(locale=locale,source_game=str(source),original_game=str(original),config=cfg,files=files,modified=modified,
           font='Fonts/'+font.name,font_sha256=sha(font.read_bytes()),license_sha256=sha((out/'Fonts/OFL.txt').read_bytes()),
           translation_inputs=fm['translation_inputs'],audio_video_transcoded=False,formal_game_changed=False)
    save(out/'DIFF_FILE.json',m)
    launcher='''$ErrorActionPreference = 'Stop'
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$m = Get-Content -LiteralPath (Join-Path $here 'DIFF_FILE.json') -Raw | ConvertFrom-Json
foreach ($entry in $m.modified.PSObject.Properties) {
 if ((Get-FileHash -LiteralPath (Join-Path $here $entry.Name)).Hash.ToLowerInvariant() -ne $entry.Value) { throw ('Resource hash mismatch: '+$entry.Name) }
}
if ((Get-FileHash -LiteralPath (Join-Path $here $m.font)).Hash.ToLowerInvariant() -ne $m.font_sha256) { throw 'Local subtitle font hash mismatch' }
Push-Location (Join-Path $here 'System')
try { & .\\WoT.exe } finally { Pop-Location }
'''
    launcher=portable_launcher(launcher)
    (out/'LAUNCH_GAME.ps1').write_text(launcher,'utf8')
    (out/'ROLLBACK.sh').write_text('#!/usr/bin/env bash\nset -euo pipefail\ncd "'+str(ROOT).replace('\\','/')+'"\npython -X utf8 -m tools.build.build_local_font_poc rollback --allow-runtime-config --input "'+str(out).replace('\\','/')+'" --out "${1:?Supply a NEW rollback-copy directory}"\n','utf8');os.chmod(out/'ROLLBACK.sh',0o755)
    verify(out)
    for row in files:
        if sha((source/row['file']).read_bytes())!=row['source_sha256']:raise ValueError('Source changed')
    print('LOCAL FONT GAME BUILD PASS: 14 movies / 628 cues; 1080p; private font bundled; no game launch; formal/source games unchanged')


def verify_file_identity(folder, manifest, allow_runtime_config=False):
    changed=[]
    for row in manifest['files']:
        name=row['file']
        expected=manifest['modified'].get(name,row['source_sha256'])
        if sha((folder/name).read_bytes())!=expected:
            if allow_runtime_config and name in {'System/WoT.ini','System/User.ini'} and name not in manifest['modified']:
                changed.append(name)
            else:
                raise ValueError('Game identity changed: '+name)
    return changed


def verify(folder, allow_runtime_config=False):
    m=load(folder/'DIFF_FILE.json');profile=load(ROOT/'profiles/fmv-movies.json')
    if sha((folder/m['font']).read_bytes())!=m['font_sha256'] or sha((folder/'Fonts/OFL.txt').read_bytes())!=m['license_sha256']:raise ValueError('Font/license changed')
    changed=verify_file_identity(folder,m,allow_runtime_config)
    for p in profile['movies']:
        data=(folder/'Movies'/p['movie']).read_bytes()
        if p['track_id'] is None:
            if sha(data)!=p['sha256']:raise ValueError('Uncaptioned movie changed')
            continue
        original=restore_movie(data,load(folder/'diffs'/(p['movie']+'.json')))
        if sha(original)!=p['sha256']:raise ValueError('Movie rollback failed')
        translations=read_translations(ROOT/'locales'/m['locale']/'fmv'/(Path(p['movie']).stem+'.tsv'))
        for sample,known in zip(text_tables(data,p['track_id'])['samples'],p['samples']):
            expected=wrap(translations[sample['index']],m['config']['line_units']) if known['nonempty'] else ''
            if sample['text']!=expected or sample['begin']!=known['begin'] or sample['duration']!=known['duration']:raise ValueError('Text/timing changed')
    dll=(folder/'System/WinDrv.dll').read_bytes();restore_dll(dll,load(folder/'diffs/local-font-loader.json'))
    if dll!=(folder/'MODIFIED_FILE.dll').read_bytes():raise ValueError('Evidence DLL differs')
    if changed:print('RUNTIME CONFIG CHANGES PRESERVED: '+', '.join(changed))
    print('LOCAL FONT VERIFY PASS: 14 movie text/timelines/media rollback; private-font DLL rollback; subset/license; immutable files unchanged')


def rollback(folder,out,allow_runtime_config=False):
    folder,out=folder.resolve(),out.resolve()
    if out.exists() or out.is_relative_to(folder) or folder.is_relative_to(out):raise ValueError('Use a NEW separate rollback copy')
    verify(folder,allow_runtime_config);m=load(folder/'DIFF_FILE.json');(out/'Movies').mkdir(parents=True);(out/'System').mkdir()
    for name in m['modified']:
        if name.startswith('Movies/'):
            data=restore_movie((folder/name).read_bytes(),load(folder/'diffs'/(Path(name).name+'.json')))
        else:data=restore_dll((folder/name).read_bytes(),load(folder/'diffs/local-font-loader.json'))
        (out/name).write_bytes(data)
        if data!=(Path(m['original_game'])/name).read_bytes():raise ValueError('Original restoration failed')
    print('LOCAL FONT ROLLBACK PASS: 14 original MOVs and WinDrv.dll restored byte-for-byte on separate copy; font game remains changed')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('mode',choices=['build','verify','rollback']);
    for name in ['source-game','original-game','font','config','input','out']:p.add_argument('--'+name,type=Path)
    p.add_argument('--locale',default='zh-CN');p.add_argument('--allow-runtime-config',action='store_true',help='Allow only unpatched WoT.ini/User.ini changes after gameplay; keep resource hash checks');a=p.parse_args()
    if a.mode=='build':
        if not all([a.source_game,a.original_game,a.font,a.config,a.out]):p.error('All build inputs required')
        build(a.source_game,a.original_game,a.font,a.config,a.out,a.locale)
    elif a.mode=='verify':verify(a.input,a.allow_runtime_config)
    else:rollback(a.input,a.out,a.allow_runtime_config)
