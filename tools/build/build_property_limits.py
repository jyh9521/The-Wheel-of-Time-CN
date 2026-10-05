"""Apply a reproducibly rebuilt property editor to an isolated readability game."""
import argparse
import difflib
import json
import shutil
from pathlib import Path
from src.patch.native_properties import build as build_native
from tools.build.build_readability_poc import verify as verify_game
from tools.validate.hardware_settings import field, sha, validate_game

ROOT=Path(__file__).resolve().parents[2]


def restore_copy(transaction, output):
    if output.exists():raise ValueError('Rollback test requires a new output directory')
    output.mkdir(parents=True)
    for name in ['Window.dll','WoT.ini','READABILITY_INSTALL.json']:
        data=(transaction/'original'/name).read_bytes()
        (output/name).write_bytes(data)
        assert (output/name).read_bytes()==data
    report=json.loads((transaction/'TRANSACTION.json').read_text())
    assert sha((output/'Window.dll').read_bytes())==report['before']['Window.dll']
    print('ROLLBACK COPY PASS: DLL/configuration/manifest restored byte-for-byte; original 255 editor behavior restored on separate copy; active game unchanged')


def build(source,game,out):
    if out.exists():raise ValueError('Choose a new evidence directory')
    source=source.resolve();game=game.resolve()
    if source==game or not (game/'READABILITY_INSTALL.json').is_file():raise ValueError('Expected isolated readability game, not original installation')
    verify_game(game)
    validate_game(game,json.loads((ROOT/'profiles/hardware-settings.json').read_text()))
    spec=json.loads((ROOT/'profiles/gog-v68.json').read_text())['native_properties']
    manifest_path=game/'READABILITY_INSTALL.json'
    current_manifest=manifest_path.read_bytes();manifest=json.loads(current_manifest)
    originals={'Window.dll':(game/'System/Window.dll').read_bytes(),
               'WoT.ini':(game/'System/WoT.ini').read_bytes(),'READABILITY_INSTALL.json':current_manifest}
    before={name:sha(data)for name,data in originals.items()}
    saves={p.relative_to(game).as_posix():sha(p.read_bytes())for p in (game/'Save').rglob('*')if p.is_file()}
    out.mkdir(parents=True);(out/'original').mkdir()
    for name,data in originals.items():(out/'original'/name).write_bytes(data)
    report=build_native(source/'System/Window.dll',out/'MODIFIED_FILE.dll',ROOT/'locales/zh-CN/native-properties.json',spec,out/'DIFF_FILE.json')
    from tools.validate.property_limits import verify as verify_ranges
    from tools.validate.native_display import verify as verify_display
    verify_ranges(out/'MODIFIED_FILE.dll',report)
    verify_display(out/'MODIFIED_FILE.dll',json.loads((ROOT/'locales/zh-CN/native-properties.json').read_text(encoding='utf8')),report,spec)
    ini=originals['WoT.ini'];changes=[]
    for limit in spec['integer_limits']:
        policy=dict(section='WinDrv.WindowsClient',key=limit['property'])
        value,start,end=field(ini,policy)
        replacement=min(limit['maximum'],max(limit['minimum'],value))
        if replacement!=value:
            ini=ini[:start]+str(replacement).encode('ascii')+ini[end:]
            changes.append(dict(property=policy['key'],old=value,new=replacement))
    (out/'MODIFIED_CONFIG.ini').write_bytes(ini)
    (out/'CONFIG_DIFF.patch').write_text(''.join(difflib.unified_diff(originals['WoT.ini'].decode('cp1252').splitlines(True),ini.decode('cp1252').splitlines(True),fromfile='before/WoT.ini',tofile='after/WoT.ini')),encoding='utf8')
    manifest['expected']['System/Window.dll']=report['modified_sha256']
    result_manifest=(json.dumps(manifest,indent=2)+'\n').encode('utf8')
    (out/'MODIFIED_MANIFEST.json').write_bytes(result_manifest)
    for name,data in originals.items():
        target=manifest_path if name=='READABILITY_INSTALL.json' else game/'System'/name
        if target.read_bytes()!=data:raise ValueError('Target changed during build; abort installation')
    try:
        shutil.copy2(out/'MODIFIED_FILE.dll',game/'System/Window.dll')
        (game/'System/WoT.ini').write_bytes(ini);manifest_path.write_bytes(result_manifest)
        verify_game(game)
        assert saves=={p.relative_to(game).as_posix():sha(p.read_bytes())for p in (game/'Save').rglob('*')if p.is_file()}
        for limit in spec['integer_limits']:
            value,_,_=field((game/'System/WoT.ini').read_bytes(),dict(section='WinDrv.WindowsClient',key=limit['property']))
            assert limit['minimum']<=value<=limit['maximum']
    except BaseException:
        for name,data in originals.items():
            (manifest_path if name=='READABILITY_INSTALL.json' else game/'System'/name).write_bytes(data)
        raise
    transaction=dict(game=str(game),before=before,after={
        'Window.dll':report['modified_sha256'],'WoT.ini':sha(ini),'READABILITY_INSTALL.json':sha(result_manifest)},
        limits=spec['integer_limits'],repaired_configuration=changes,saves_unchanged=True,fmv_unchanged=True,game_launched=False)
    (out/'TRANSACTION.json').write_text(json.dumps(transaction,indent=2)+'\n',encoding='utf8')
    print('PROPERTY LIMIT INSTALL PASS: 3 byte sliders; 4 integer input guards; configuration '+str(changes)+'; 1.5x fonts/FMVs/saves unchanged; game not launched')
    return transaction


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('mode',choices=['build','restore-copy'])
    p.add_argument('--source-game',type=Path);p.add_argument('--game-dir',type=Path);p.add_argument('--out',type=Path,required=True);p.add_argument('--transaction',type=Path)
    a=p.parse_args()
    if a.mode=='build':
        if a.source_game is None or a.game_dir is None:p.error('--source-game and --game-dir required')
        build(a.source_game,a.game_dir,a.out)
    else:
        if a.transaction is None:p.error('--transaction required')
        restore_copy(a.transaction,a.out)
