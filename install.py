"""Install/verify/restore a trusted locally built, version-guarded delta bundle."""

import argparse
import json
import os
import sys
from pathlib import Path
from src.patch.delta import apply, sha


def atomic(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + ".localization-write")
    try:
        temp.write_bytes(data)
        os.replace(temp, path)
    finally:
        if temp.exists():
            temp.unlink()


def targets(target, bundle):
    if bundle["format"] != "localization-bundle-v1" or not bundle["files"]:
        raise ValueError("Invalid bundle format")
    paths = {}
    for name in bundle["files"]:
        p = Path(name)
        verified_display_dll = False
        if name == 'System/Window.dll':
            profile = json.loads((Path(__file__).resolve().parent / 'profiles/gog-v68.json').read_text('utf8'))
            expected = profile['files'].get(name)
            delta = bundle['files'][name]
            verified_display_dll = bool(expected and bundle.get('profile') == profile['id']
                and delta.get('original_sha256') == expected['sha256']
                and delta.get('original_size') == expected['size'])
        if (
            p.is_absolute()
            or len(p.parts) != 2
            or p.parts[0] != "System"
            or (p.suffix.lower() not in (".u", ".int") and not verified_display_dll)
            or ":" in name
            or "\\" in name
        ):
            raise ValueError("Invalid bundle path: " + name)
        dest = (target / p).resolve()
        if not dest.is_relative_to(target) or (target / p).is_symlink():
            raise ValueError("Target path escapes installation")
        paths[name] = dest
    return paths


def transaction(command, bundle_path, target):
    target = target.resolve()
    bundle = json.loads(bundle_path.read_text("utf8"))
    paths = targets(target, bundle)
    backup = target / ".localization-backup"
    if backup.is_symlink() or not backup.resolve().is_relative_to(target):
        raise ValueError("Invalid backup directory")
    staged = {}
    for name, path in paths.items():
        delta = bundle["files"][name]
        current = path.read_bytes()
        if command == "apply":
            staged[name] = apply(current, delta)
            saved = backup / name
            if not saved.resolve().is_relative_to(backup.resolve()):
                raise ValueError("Backup path escapes directory")
            if saved.exists() and sha(saved.read_bytes()) != delta["original_sha256"]:
                raise ValueError("Existing backup differs: " + name)
        elif command == "verify":
            if (
                sha(current) != delta["modified_sha256"]
                or len(current) != delta["modified_size"]
            ):
                raise ValueError("Installed resource differs: " + name)
        else:
            if sha(current) not in (delta["original_sha256"], delta["modified_sha256"]):
                raise ValueError("Resource changed since install: " + name)
            saved = backup / name
            if not saved.resolve().is_relative_to(backup.resolve()):
                raise ValueError("Backup path escapes directory")
            original = saved.read_bytes()
            if (
                sha(original) != delta["original_sha256"]
                or len(original) != delta["original_size"]
            ):
                raise ValueError("Backup differs: " + name)
            staged[name] = original
    # Preflight all files before any write; preserve immutable backups first.
    previous = {name: p.read_bytes() for name, p in paths.items()}
    if command == "apply":
        for name, data in previous.items():
            saved = backup / name
            if not saved.exists():
                atomic(saved, data)
    try:
        for name, data in staged.items():
            atomic(paths[name], data)
        for name, path in paths.items():
            expected = bundle["files"][name][
                "original_sha256" if command == "restore" else "modified_sha256"
            ]
            if sha(path.read_bytes()) != expected:
                raise ValueError("Readback failed: " + name)
    except Exception:
        for name, data in previous.items():
            atomic(paths[name], data)
        raise
    print(
        f"{command.upper()} PASS: {len(paths)} files; "
        + ("original SHA-256 restored" if command == "restore" else "SHA-256 verified")
    )


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("command", choices=["apply", "verify", "restore"])
    p.add_argument("--bundle", type=Path, required=True)
    p.add_argument("--target", type=Path, required=True)
    a = p.parse_args()
    try:
        transaction(a.command, a.bundle, a.target)
    except (ValueError, OSError, KeyError) as exc:
        print("ERROR: " + str(exc), file=sys.stderr)
        sys.exit(1)
