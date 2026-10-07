"""Local-only ready-to-copy test bundle; never publish complete game-derived files."""
import argparse
import json
from pathlib import Path
import re
import sys
import zipfile

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from src.patch.delta import sha
from tools.pack.dialog_resources import patch


def configure(data, sections):
    codec='utf-16' if data.startswith(b'\xff\xfe') else 'cp1252'
    text=data.decode(codec)
    for section, values in sections.items():
        pattern=re.compile(r'(?ms)^\['+re.escape(section)+r'\][^\r\n]*\r?\n(.*?)(?=^\[|\Z)')
        match=pattern.search(text)
        if not match:
            text+='\r\n['+section+']\r\n'+''.join(k+'='+v+'\r\n' for k,v in values.items())
            continue
        block=match.group()
        for key,value in values.items():
            regex=re.compile(r'(?m)^'+re.escape(key)+r'=[^\r\n]*')
            block,n=regex.subn(lambda _:key+'='+value,block)
            if not n:
                block+=key+'='+value+'\r\n'
        text=text[:match.start()]+block+text[match.end():]
    return text.encode(codec)


def package(game, runtime, delta_package, out, work, locale):
    with zipfile.ZipFile(delta_package) as z:
        manifest=json.loads(z.read('LocalizationTest/MANIFEST.json'))
    if manifest['locale']!=locale:
        raise ValueError('Locale differs')
    # The delta package is the hash-gated inventory, not an installer shipped to
    # players. Cross-check every original and every prepared output first.
    for e in manifest['files']:
        if not e['owned']:
            if sha((game/e['path']).read_bytes())!=e['original_sha256']:
                raise ValueError('Original differs: '+e['path'])
        if sha((runtime/e['path']).read_bytes())!=e['modified_sha256']:
            raise ValueError('Runtime differs: '+e['path'])
    work.mkdir(parents=True,exist_ok=True)
    rows=json.loads((ROOT/'locales'/locale/'startup-dialogs.json').read_text('utf-8'))
    window=work/'System/Window.dll'
    original_window=runtime/'System/Window.dll'
    launcher=patch(original_window,window,sha(original_window.read_bytes()),rows)
    (work/'LAUNCHER_DIFF.json').write_text(json.dumps(launcher,ensure_ascii=False,indent=2),encoding='utf-8')
    configs=json.loads((ROOT/'locales'/locale/'player-config.json').read_text('utf-8'))
    config_data={name:configure((game/name).read_bytes(),fields) for name,fields in configs.items()}
    config_data['System/WoT.ini']=config_data['System/Default.ini']
    config_data['System/User.ini']=config_data['System/DefUser.ini']
    paths={e['path']:window if e['path']=='System/Window.dll' else runtime/e['path'] for e in manifest['files']}
    identity={}
    out.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(out,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=1) as z:
        for name in sorted(set(paths)|set(config_data)):
            data=config_data[name] if name in config_data else paths[name].read_bytes()
            info=zipfile.ZipInfo(name,(2020,1,1,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED
            z.writestr(info,data,compresslevel=1)
            original=(game/name).read_bytes() if (game/name).exists() else None
            identity[name]={'size':len(data),'sha256':sha(data),'original_sha256':sha(original) if original is not None else None}
        notes=(ROOT/'docs/OVERLAY_TEST_PACKAGE.md').read_bytes()
        z.writestr('汉化测试说明.txt',notes)
        z.writestr('汉化文件清单.json',json.dumps({'locale':locale,'files':identity,'normal_entry':'System/WoT.exe','launch_arguments':[]},ensure_ascii=False,indent=2))
    with zipfile.ZipFile(out) as z:
        if z.testzip():raise ValueError('ZIP CRC failed')
        for name,row in identity.items():
            if sha(z.read(name))!=row['sha256']:raise ValueError('ZIP readback differs')
        if any(n.endswith(('.cmd','.ps1')) for n in z.namelist()):raise ValueError('Player scripts must not be shipped')
        if 'System/WoT.exe' in z.namelist():raise ValueError('Game executable must remain original')
    out.with_suffix('.zip.sha256').write_text(sha(out.read_bytes())+'  '+out.name+'\n',encoding='ascii')
    (work/'DIFF_FILE.json').write_text(json.dumps({'files':identity,'launcher':launcher},ensure_ascii=False,indent=2),encoding='utf-8')
    print(f'OVERLAY PACKAGE PASS: files={len(identity)}; no CMD/PS1; original WoT.exe; startup wizard captions localized; bytes={out.stat().st_size}')
    return identity


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('game-dir','runtime-dir','delta-package','out','work'):
        p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--locale',default='zh-CN');a=p.parse_args()
    package(a.game_dir,a.runtime_dir,a.delta_package,a.out,a.work,a.locale)
