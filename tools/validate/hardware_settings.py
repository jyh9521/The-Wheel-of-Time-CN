"""Check/recover the profiled hardware-menu detail selector without resetting settings."""
import argparse,difflib,hashlib,json,re,shutil
from pathlib import Path
from tools.pack.ue1 import Package,body
ROOT=Path(__file__).resolve().parents[2]

def sha(data):return hashlib.sha256(data).hexdigest()

def field(data,policy):
    section=policy['section'].encode('ascii');key=policy['key'].encode('ascii')
    active=False;matches=[];start=0;sections=0
    for line in data.splitlines(keepends=True):
        header=re.fullmatch(rb'\s*\[([^]\r\n]+)\]\s*',line)
        if header:
            active=header[1].lower()==section.lower()
            if active:sections+=1
        if active:
            m=re.fullmatch(rb'([ \t]*'+re.escape(key)+rb'[ \t]*=[ \t]*)([0-9]+)([ \t]*(?:;[^\r\n]*)?)(\r?\n)?',line,re.I)
            if m:matches.append((int(m[2]),start+m.start(2),start+m.end(2)))
        start+=len(line)
    if sections!=1 or len(matches)!=1:raise ValueError('Expected one profiled section/key; do not guess ambiguous configuration')
    return matches[0]

def repaired(data,policy):
    value,begin,end=field(data,policy)
    if value in policy['allowed']:raise ValueError('Selector already valid; no repair needed')
    replacement=str(policy['recovery_value']).encode('ascii')
    result=data[:begin]+replacement+data[end:]
    assert field(result,policy)[0] in policy['allowed']
    assert result[:begin]==data[:begin] and result[begin+len(replacement):]==data[end:]
    return result

def validate_game(game,policy):
    package=Package(game/'System/WOT.u')
    matches=[r for r in package.records()if r['path']==policy['export'] and r['class_name']=='Function']
    if package.ver!=policy['package_version'] or len(matches)!=1 or sha(body(package,matches[0]['index']))!=policy['export_sha256']:
        raise ValueError('Unknown hardware menu function; inspect version before recovery')

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('mode',choices=['check','repair']);p.add_argument('--game-dir',type=Path,required=True);p.add_argument('--out',type=Path);p.add_argument('--profile',type=Path,default=ROOT/'profiles/hardware-settings.json');args=p.parse_args()
    policy=json.loads(args.profile.read_text(encoding='utf8'));validate_game(args.game_dir,policy)
    ini=args.game_dir/'System/WoT.ini';before=ini.read_bytes();value,_,_=field(before,policy)
    if args.mode=='check':
        if value not in policy['allowed']:
            print(f"HARDWARE CONFIG INVALID: {policy['key']}={value}; allowed=0,1,2; original hardware menu asserts outside range")
            return 1
        print(f"HARDWARE CONFIG PASS: {policy['key']}={value}; menu selector within profiled range")
        return 0
    if args.out is None or args.out.exists():p.error('--out must be a NEW recovery evidence directory')
    result=repaired(before,policy);args.out.mkdir(parents=True)
    (args.out/'ORIGINAL_FILE.ini').write_bytes(before);(args.out/'MODIFIED_FILE.ini').write_bytes(result)
    log=args.game_dir/'System/WoT.log'
    if log.exists():shutil.copy2(log,args.out/'CRASH_BEFORE.log')
    (args.out/'DIFF_FILE.patch').write_text(''.join(difflib.unified_diff(before.decode('cp1252').splitlines(True),result.decode('cp1252').splitlines(True),fromfile='original/WoT.ini',tofile='repaired/WoT.ini')),encoding='utf8')
    manifest=dict(file=str(ini.resolve()),before_sha256=sha(before),after_sha256=sha(result),field=policy['key'],old=value,new=policy['recovery_value'],only_numeric_value_changed=True)
    (args.out/'RECOVERY.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf8')
    if ini.read_bytes()!=before:raise ValueError('Configuration changed during recovery')
    ini.write_bytes(result)
    if ini.read_bytes()!=result:raise ValueError('Configuration readback mismatch')
    print(f"HARDWARE CONFIG REPAIR PASS: {policy['key']} {value}->{policy['recovery_value']}; all other configuration bytes and saves unchanged; backup/log retained; game not launched")
    return 0

if __name__=='__main__':raise SystemExit(main())
