"""Guarded one-resource upgrade of an existing player-test installation."""
import argparse,hashlib,json,os,shutil
from pathlib import Path
RESOURCE='System/SubtitleRuntime.u'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def put(p,data):
    temp=p.with_name(p.name+'.caption-update.tmp')
    if temp.exists():raise ValueError('Temporary output already exists')
    temp.write_bytes(data);os.replace(temp,p)
def update(target,old_path,new_path,replacement,receipt,restore=False):
    old=json.loads(old_path.read_text('utf8'));new=json.loads(new_path.read_text('utf8'))
    if old['format']!='player-test-v1' or new['format']!=old['format']:raise ValueError('Unknown format')
    before={e['path']:e for e in old['files']};after={e['path']:e for e in new['files']}
    if set(before)!=set(after) or any(before[k]!=after[k] for k in before if k!=RESOURCE):raise ValueError('Only owned subtitle runtime may change')
    if not before[RESOURCE]['owned'] or not after[RESOURCE]['owned']:raise ValueError('Not an owned resource')
    if sha(replacement)!=after[RESOURCE]['modified_sha256']:raise ValueError('Replacement identity mismatch')
    if any(e['path'].startswith('/') or '..' in e['path'] or ':' in e['path'] for e in old['files']):raise ValueError('Invalid resource path')
    state=target/'.localization-backup/player-test/STATE.json';runtime=target/RESOURCE
    expected=after if restore else before
    config=json.loads(state.read_text('utf-8-sig'))
    wanted=sha(new_path) if restore else sha(old_path)
    if config['manifest_sha256']!=wanted:raise ValueError('Installation manifest differs')
    for name,e in expected.items():
        file=target/name
        if file.stat().st_size!=e['modified_size'] or sha(file)!=e['modified_sha256']:raise ValueError('Installed resource differs: '+name)
    if restore:
        record=json.loads((receipt/'RECEIPT.json').read_text('utf8'))
        if sha(receipt/'SubtitleRuntime.u')!=before[RESOURCE]['modified_sha256'] or sha(receipt/'STATE.json')!=record['state_sha256']:raise ValueError('Receipt backup differs')
        put(runtime,(receipt/'SubtitleRuntime.u').read_bytes());put(state,(receipt/'STATE.json').read_bytes())
        print('ROLLBACK PASS: prior SubtitleRuntime.u and installer state restored; settings and saves untouched')
    else:
        receipt.mkdir(parents=True,exist_ok=False);shutil.copy2(runtime,receipt/'SubtitleRuntime.u');shutil.copy2(state,receipt/'STATE.json')
        (receipt/'RECEIPT.json').write_text(json.dumps(dict(target=str(target),before_sha256=sha(runtime),after_sha256=sha(replacement),state_sha256=sha(state)),indent=2),'utf8')
        try:
            put(runtime,replacement.read_bytes());config['manifest_sha256']=sha(new_path)
            put(state,(json.dumps(config,ensure_ascii=False,indent=2)+'\n').encode('utf8'))
            if sha(runtime)!=after[RESOURCE]['modified_sha256']:raise ValueError('Readback differs')
        except Exception:
            put(runtime,(receipt/'SubtitleRuntime.u').read_bytes());put(state,(receipt/'STATE.json').read_bytes());raise
        print('UPDATE PASS: one owned SubtitleRuntime.u changed; installer manifest aligned; settings and saves untouched')
if __name__=='__main__':
    p=argparse.ArgumentParser()
    for name in ['target','old-manifest','new-manifest','replacement','receipt']:p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--restore',action='store_true');a=p.parse_args()
    update(a.target.resolve(),a.old_manifest,a.new_manifest,a.replacement,a.receipt,a.restore)
