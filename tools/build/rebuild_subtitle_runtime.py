"""Recompile the owned subtitle package without changing fonts or game resources."""
import argparse,hashlib,json,shutil,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from tools.pack.ue1 import Package
from tools.build.subtitle_runtime import validate_cues
from tools.build.runtime_messages import bind

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def rebuild(game,locale,out):
    config=json.loads((ROOT/'locales'/locale/'config.json').read_text('utf8'))
    profile=json.loads((ROOT/'profiles/subtitle-runtime.json').read_text('utf8'))
    for e in profile['compiler_inputs']:
        p=game/e['file']
        if sha(p)!=e['sha256'] or p.stat().st_size!=e['size']:raise ValueError('Unknown compiler input: '+e['file'])
    cues=json.loads((ROOT/'locales'/locale/config['subtitle_display']['cues']).read_text('utf8'))
    section,key=cues['sound'].split('.')
    rows=json.loads((ROOT/'locales'/locale/config['subtitle_overrides']).read_text('utf8'))
    row=next(r for r in rows if r['section']==section and r['key']==key)
    if row['source_sha256']!=cues['source_sha256']:raise ValueError('Cue identity changed')
    validate_cues(cues,row['translation']);messages=bind(game,config,ROOT)
    out.mkdir(parents=True,exist_ok=False);system=out/'compiler/System';system.mkdir(parents=True)
    for p in (game/'System').iterdir():
        if p.suffix.lower() in ('.dll','.int') or p.name in ('UCC.exe','Default.ini','DefUser.ini'):shutil.copy2(p,system/p.name)
    classes=out/'compiler/SubtitleRuntime/Classes';classes.mkdir(parents=True)
    for name in ('CaptionState','SubtitleHUD'):
        text=(ROOT/'src/runtime/SubtitleRuntime/Classes'/ (name+'.uc')).read_text('utf8')
        text='\n'.join(line if line.isascii() else '// Subtitle runtime.' for line in text.splitlines())
        if name=='SubtitleHUD':
            text+='\ndefaultproperties\n{\n CueCount='+str(len(cues['cues']))+'\n MessageCount='+str(len(messages))+'\n'
            for i,c in enumerate(cues['cues']):text+=f" CueBegin({i})={c['begin']}\n CueEnd({i})={c['end']}\n"
            text+='}\n'
        (classes/(name+'.uc')).write_text(text,'ascii')
    ini='[Core.System]\nPaths='+str(system/'*.u')+'\n'
    for d,pattern in [('System','*.u'),('Textures','*.utx'),('Sounds','*.uax'),('Music','*.umx')]:ini+='Paths='+str(game/d/pattern)+'\n'
    ini+='[Engine.Engine]\nEditorEngine=Editor.EditorEngine\nLanguage=int\n[Editor.EditorEngine]\n'
    ini+=''.join('EditPackages='+n+'\n' for n in ['Core','Engine','Legend','WOT','Angreal','WOTPawns','SubtitleRuntime'])
    (system/'WoT.ini').write_text(ini,'ascii')
    cmd=[str(system/'UCC.exe'),'Editor.MakeCommandlet','-ini=WoT.ini']
    proc=subprocess.run(cmd,cwd=system,capture_output=True)
    log=proc.stdout.decode('cp1252')+proc.stderr.decode('cp1252');(out/'COMPILER.txt').write_text(log,'utf8')
    if proc.returncode or 'Success - 0 error(s), 0 warnings' not in log:raise ValueError('Compilation failed; see COMPILER.txt')
    binary=system/'SubtitleRuntime.u';raw=bytearray(binary.read_bytes());raw[36:52]=hashlib.sha256(raw[:36]+raw[52:]).digest()[:16];binary.write_bytes(raw)
    pkg=Package(binary);names={r['path'] for r in pkg.records() if pkg.exports[r['index']-1]['cls']==0}
    if not {'CaptionState','SubtitleHUD'}<=names:raise ValueError('Missing runtime classes')
    dst=out/'MODIFIED_FILE.u';shutil.copy2(binary,dst)
    (out/'DIFF_FILE.json').write_text(json.dumps(dict(source_classes=['CaptionState','SubtitleHUD'],modified_sha256=sha(dst),compiler_command=cmd,compiler_exit_status=proc.returncode,fonts_changed=False,maps_changed=False),indent=2),'utf8')
    print('RUNTIME REBUILD PASS: 0 errors; 0 warnings; CaptionState and SubtitleHUD exports verified; fonts/maps unchanged')
    return dst
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--game-dir',type=Path,required=True);p.add_argument('--locale',default='zh-CN');p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    if (ROOT/'locales'/a.locale).resolve().parent!=(ROOT/'locales').resolve():raise ValueError('Invalid locale')
    if a.out.resolve().is_relative_to(a.game_dir.resolve()):raise ValueError('Use independent output')
    rebuild(a.game_dir.resolve(),a.locale,a.out.resolve())
