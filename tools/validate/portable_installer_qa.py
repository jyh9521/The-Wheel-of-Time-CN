"""Exercise the final embedded EXE through its production backend; no game launch."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def qa(original,exe,manifest,work):
    work.mkdir(parents=True,exist_ok=True)
    game=work/'新装 GOG 验证'
    if game.exists():raise ValueError('QA destination must be new')
    game.mkdir()
    for name in ('System','Maps','Textures','Sounds','Music','Movies'):shutil.copytree(original/name,game/name)
    spec=json.loads(manifest.read_text(encoding='utf-8'))
    # Exercise enabling a disabled switch without importing private bindings.
    user=game/'System/User.ini';raw=user.read_bytes();codec='utf-16' if raw.startswith(b'\xff\xfe') else 'cp1252'
    import re
    user.write_bytes(re.sub(r'(?im)^bSubtitles=[^\r\n]*','bSubtitles=False',raw.decode(codec)).encode(codec))
    before={p.relative_to(game).as_posix():sha(p) for p in game.rglob('*') if p.is_file()}
    configs={c['path']:(game/c['path']).read_bytes() for c in spec['config']}
    save=game/'Save/test-progress.sentinel';save.parent.mkdir(exist_ok=True);save.write_bytes(b'keep progress')
    records=[]
    def run(action,expect=0):
        log=work/f'{len(records):02}-{action}.log'
        cmd=[str(exe.resolve()),'--headless',action,str(game.resolve()),str(log.resolve())]
        proc=subprocess.run(cmd,timeout=300)
        output=log.read_text(encoding='utf-8') if log.exists() else 'NO LOG'
        record=dict(command=subprocess.list2cmdline(cmd),input=action,output=output.strip(),exit_status=proc.returncode)
        records.append(record);print(json.dumps(record,ensure_ascii=False),flush=True)
        if proc.returncode!=expect:raise ValueError(record)
    run('check')
    assert all(sha(game/n)==h for n,h in before.items())
    assert not (game/'.localization-backup').exists()
    import os,stat
    locked=game/'System/Window.dll'
    os.chmod(locked,stat.S_IREAD)
    try:
        run('check',1);run('apply',1)
    finally:os.chmod(locked,stat.S_IREAD|stat.S_IWRITE)
    assert all(sha(game/n)==h for n,h in before.items())
    assert not (game/'.localization-backup/player-test/STATE.json').exists()
    victim=game/spec['files'][0]['path'];clean=victim.read_bytes();victim.write_bytes(clean+b'wrong-version')
    run('check',1);run('apply',1);victim.write_bytes(clean)
    assert all(sha(game/n)==h for n,h in before.items())
    assert not (game/'.localization-backup/player-test/STATE.json').exists()
    run('apply');run('verify');run('check');run('apply')
    assert 'bSubtitles=True' in user.read_bytes().decode(codec)
    for e in spec['files']:assert sha(game/e['path'])==e['modified_sha256']
    # External modification blocks restore instead of overwriting unrelated work.
    translated=victim.read_bytes();victim.write_bytes(translated+b'external-edit')
    run('restore',1);victim.write_bytes(translated)
    run('restore')
    for n,h in before.items():assert sha(game/n)==h
    for c,b in configs.items():assert (game/c).read_bytes()==b
    for e in spec['files']:
        if e['owned']:assert not (game/e['path']).exists()
    assert save.read_bytes()==b'keep progress'
    run('apply');run('verify')
    (work/'VERIFICATION.json').write_text(json.dumps(dict(records=records,resources=len(spec['files']),
        exe_sha256=sha(exe),rollback='Original file/config hashes restored; additions removed; saves retained',
        final_status='Localized independent copy retained; original installation unchanged; game not launched'),ensure_ascii=False,indent=2),encoding='utf-8')
    print('PORTABLE EXE QA PASS: check without writes; unknown-version rejection; install; verify; guarded restore; reinstall; saves preserved')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('game-dir','exe','manifest','work'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();qa(a.game_dir,a.exe,a.manifest,a.work)
