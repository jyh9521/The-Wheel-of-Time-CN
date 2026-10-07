"""Restore a local overlay QA copy using a separately retained original tree."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil


def restore(original,target,manifest):
    original,target=original.resolve(),target.resolve()
    if original==target or original in target.parents or target in original.parents:
        raise ValueError('Original and restore destination must be independent')
    spec=json.loads(manifest.read_text(encoding='utf-8'))['files']
    for name,row in spec.items():
        relative=Path(name)
        if relative.is_absolute() or '..' in relative.parts:
            raise ValueError('Invalid restore path')
        dst=(target/relative).resolve()
        if not dst.is_relative_to(target):raise ValueError('Restore path escape')
        if row['original_sha256'] is not None:
            src=original/relative
            if hashlib.sha256(src.read_bytes()).hexdigest()!=row['original_sha256']:
                raise ValueError('Original changed: '+name)
        if dst.exists():
            current=hashlib.sha256(dst.read_bytes()).hexdigest()
            if current not in (row['sha256'],row['original_sha256']):raise ValueError('External edit: '+name)
    for name,row in spec.items():
        dst=target/name
        if row['original_sha256'] is None:
            if dst.exists():dst.unlink()
        else:
            dst.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(original/name,dst)
            if hashlib.sha256(dst.read_bytes()).hexdigest()!=row['original_sha256']:raise ValueError('Restore readback failed')
    print(f'ROLLBACK PASS: {len(spec)} file states restored; added resources removed; original behavior/configuration restored')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--original',type=Path,required=True);p.add_argument('--target',type=Path,required=True);p.add_argument('--manifest',type=Path,required=True)
    a=p.parse_args();restore(a.original,a.target,a.manifest)
