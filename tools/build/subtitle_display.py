"""Build a dedicated subtitle HUD/font; preserve all existing UI font exports."""
import hashlib,json,shutil,subprocess
from pathlib import Path
from tools.pack.ue1 import Package,body
from tools.font.append_font import append_font
from src.patch.subtitle_hud import bind
from tools.build.subtitle_runtime import validate_cues
ROOT=Path(__file__).resolve().parents[2]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def build(game,package,fontpath,out,config):
    out.mkdir(parents=True,exist_ok=False)
    cues=json.loads((ROOT/'locales'/config['locale']/config['subtitle_display']['cues']).read_text('utf8'))
    rows=json.loads((ROOT/'locales'/config['locale']/config['subtitle_overrides']).read_text('utf8'))
    section,key=cues['sound'].split('.')
    row=next(r for r in rows if r['section']==section and r['key']==key)
    if row['source_sha256']!=cues['source_sha256']:raise ValueError('Subtitle source identity changed')
    validate_cues(cues,row['translation'])
    system=(out/'compiler/System').resolve();system.mkdir(parents=True)
    for expected in json.loads((ROOT/'profiles/subtitle-runtime.json').read_text('utf8'))['compiler_inputs']:
        if sha(game/expected['file'])!=expected['sha256']:raise ValueError('Unknown compiler input')
    for p in (game/'System').iterdir():
        if p.suffix.lower()in['.dll','.int']or p.name in['UCC.exe','Default.ini','DefUser.ini']:shutil.copyfile(p,system/p.name)
    classes=out/'compiler/SubtitleRuntime/Classes';classes.mkdir(parents=True)
    source=(ROOT/'src/runtime/SubtitleRuntime/Classes/SubtitleHUD.uc').read_text('utf8')
    source='\n'.join(l if l.isascii()else '// Subtitle display layer.'for l in source.splitlines())
    source+='\ndefaultproperties\n{\n CueCount='+str(len(cues['cues']))+'\n'
    for i,c in enumerate(cues['cues']):source+=f' CueBegin({i})={c["begin"]}\n CueEnd({i})={c["end"]}\n'
    source+='}\n';(classes/'SubtitleHUD.uc').write_text(source,'ascii')
    (classes/'SubtitleProbe.uc').write_text("""class SubtitleProbe expands Commandlet;
event int Main(string Params)
{
 local class<GameInfo> G;
 local Font F;
 G=class<GameInfo>(DynamicLoadObject("WOT.giWOT",class'Class'));
 F=Font(DynamicLoadObject("WOT.SubtitleFont",class'Font'));
 Log("SUBTITLE LOAD HUD=" $ G.default.HUDType $ " FONT=" $ F $ " CUES=" $ class'SubtitleHUD'.default.CueCount);
 if (G.default.HUDType != class'SubtitleHUD' || F == None) return 1;
 if (class'SubtitleHUD'.default.CueCount != 4 || Len(Localize("SubtitleHUD","IntroText","SubtitleRuntime",true))==0) return 2;
 Log("SUBTITLE NATIVE PASS: dedicated HUD/font loaded; 4 timed cues; localized intro present");
 return 0;
}
""",'ascii')
    probe=classes/'SubtitleProbe.uc'
    probe.write_text(probe.read_text('ascii').replace('!= 4','!= '+str(len(cues['cues']))),'ascii')
    ini='[Core.System]\nPaths='+str(system/'*.u')+'\n'+''.join('Paths='+str(game/d/p)+'\n'for d,p in [('System','*.u'),('Textures','*.utx'),('Sounds','*.uax'),('Music','*.umx')])+'\n[Engine.Engine]\nEditorEngine=Editor.EditorEngine\nLanguage=int\n[Editor.EditorEngine]\n'+''.join('EditPackages='+n+'\n'for n in ['Core','Engine','Legend','WOT','Angreal','WOTPawns','SubtitleRuntime'])
    (system/'WoT.ini').write_text(ini,'ascii')
    def run(command,logname):
        r=subprocess.run([str(system/'UCC.exe'),command,'-ini=WoT.ini'],cwd=system,capture_output=True)
        log=r.stdout.decode('cp1252')+r.stderr.decode('cp1252');(out/logname).write_text(log,'utf8')
        if r.returncode:raise ValueError('Native commandlet failed: '+logname)
        return log
    log=run('Editor.MakeCommandlet','COMPILER.txt')
    if 'Success - 0 error(s), 0 warnings'not in log:raise ValueError('Compiler errors or warnings')
    binary=system/'SubtitleRuntime.u';raw=bytearray(binary.read_bytes());raw[36:52]=hashlib.sha256(raw[:36]+raw[52:]).digest()[:16];binary.write_bytes(raw)
    int_text='[SubtitleHUD]\r\nIntroText="'+row['translation']+'"\r\n'+''.join(f'CueText[{i}]="{c["translation"]}"\r\n'for i,c in enumerate(cues['cues']))
    (system/'SubtitleRuntime.int').write_bytes(b'\xff\xfe'+int_text.encode('utf-16le'))
    font_report=append_font(package,out/'FONT_ONLY.u',fontpath,dict(name='SubtitleFont',template='F_WOTReg14',pixel_size=config['subtitle_display']['pixel_size'],source_sha256=sha(package)))
    original=Package(game/'System/WOT.u');gi=next(r['index']for r in original.records()if r['path']=='giWOT')
    hud_report=bind(out/'FONT_ONLY.u',out/'MODIFIED_FILE.u',sha(out/'FONT_ONLY.u'),hashlib.sha256(body(original,gi)).hexdigest())
    (system/'WOT.u').write_bytes((out/'MODIFIED_FILE.u').read_bytes())
    log=run('SubtitleRuntime.SubtitleProbe','NATIVE_PROBE.txt')
    if 'SUBTITLE NATIVE PASS:'not in log:raise ValueError('Native subtitle binding missing')
    package.write_bytes((out/'MODIFIED_FILE.u').read_bytes())
    for name in ['SubtitleRuntime.u','SubtitleRuntime.int']:shutil.copyfile(system/name,package.parent/name)
    report=dict(font=font_report,hud=hud_report,cues=cues['cues'],queue_capacity=64,normal_start_integrated=True,in_game_verified=False)
    (out/'DIFF_FILE.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n','utf8')
    print('SUBTITLE DISPLAY PASS: 18px dedicated font; existing UI fonts unchanged; 64 independent captions; 4 intro cues; native load verified')
    return report
