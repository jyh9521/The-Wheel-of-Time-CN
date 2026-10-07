"""Test literal ZIP overwrite and separate-copy restore without game launch."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import zipfile


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def qa(source,package,work):
    game=work/'qa-game';rollback=work/'rollback-game'
    if game.exists() or rollback.exists():raise ValueError('QA destinations must be new')
    game.mkdir(parents=True)
    for name in ('System','Maps','Textures','Sounds','Music','Movies'):
        shutil.copytree(source/name,game/name)
    before={p.relative_to(game).as_posix():sha(p) for p in game.rglob('*') if p.is_file()}
    original_exe=sha(game/'System/WoT.exe')
    with zipfile.ZipFile(package) as z:
        info=json.loads(z.read('汉化文件清单.json'))
        assert not any(n.endswith(('.cmd','.ps1')) for n in z.namelist())
        for n in z.namelist():
            assert not n.startswith('/') and '..' not in Path(n).parts
        z.extractall(game)  # EXACT player action: ordinary extract-and-overwrite.
    for path,row in info['files'].items():
        assert sha(game/path)==row['sha256']
    changed={p.casefold() for p in info['files']}
    for path,h in before.items():
        if path.casefold() not in changed:assert sha(game/path)==h
    assert sha(game/'System/WoT.exe')==original_exe
    user=(game/'System/User.ini').read_bytes().decode('cp1252')
    assert 'bSubtitles=True' in user
    config=(game/'System/WoT.ini').read_bytes().decode('cp1252')
    assert '[FirstRun]\r\nFirstRun=0' in config
    assert 'FullscreenViewportX=1920' in config and 'FullscreenViewportY=1080' in config
    assert 'Map=Index.wot' in config and 'LocalMap=WheelOfTime.wot' in config
    # Roll back another copy so the real QA overlay remains installed.
    rollback.mkdir()
    for path,row in info['files'].items():
        dst=rollback/path;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(game/path,dst)
    for path,row in info['files'].items():
        dst=rollback/path
        if row['original_sha256'] is None:dst.unlink()
        else:shutil.copyfile(source/path,dst);assert sha(dst)==row['original_sha256']
    for path,row in info['files'].items():
        if row['original_sha256'] is None:assert not (rollback/path).exists()
    report={'baseline':'BASELINE PASS: original resources fingerprinted; no files altered',
            'modified':f'OVERWRITE PASS: {len(info["files"])} files matched; normal WoT.exe unchanged; no scripts needed',
            'rollback':f'ROLLBACK PASS: {len(info["files"])} file states restored on another copy; QA game stays localized',
            'game_launched':False,'gog_installer_executed':False,'zip_sha256':sha(package),
            'exe_sha256':original_exe,'files':len(info['files'])}
    (work/'VERIFICATION.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    for phase in ('baseline','modified','rollback'):print(report[phase])
    return report


if __name__=='__main__':
    a=argparse.ArgumentParser(description=__doc__)
    a.add_argument('--game-dir',type=Path,required=True);a.add_argument('--package',type=Path,required=True);a.add_argument('--work',type=Path,required=True)
    p=a.parse_args();qa(p.game_dir,p.package,p.work)
