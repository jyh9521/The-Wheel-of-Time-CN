"""Exercise the extracted Windows installer without launching the game."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import zipfile
from hashlib import sha256


def digest(p):
    return sha256(p.read_bytes()).hexdigest()


def run(game, action, extra=(), expected=0):
    cmd = ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
           str(game / "LocalizationTest/Manage-Patch.ps1"), "-Action", action, "-GameDir", str(game), *extra]
    p = subprocess.run(cmd, capture_output=True, text=True)
    result = {"command": subprocess.list2cmdline(cmd), "input": action, "output": p.stdout.strip(),
              "stderr": p.stderr.strip(), "exit_status": p.returncode}
    print(json.dumps(result, ensure_ascii=False), flush=True)
    if p.returncode != expected:
        raise RuntimeError(result)
    return result


def qa(source, package, target, report):
    if target.exists():
        raise ValueError("QA target must be new")
    target.mkdir(parents=True)
    for folder in ("System", "Maps", "Textures", "Sounds", "Music", "Movies"):
        shutil.copytree(source / folder, target / folder)
    with zipfile.ZipFile(package) as z:
        if any(n.startswith('/') or '..' in Path(n).parts for n in z.namelist()):
            raise ValueError("Invalid ZIP path")
        z.extractall(target)
    manifest = json.loads((target / "LocalizationTest/MANIFEST.json").read_text())
    # Simulate a fresh configuration with subtitles off; source installation's
    # existing personal settings must not be mistaken for installer validation.
    user_ini = target / "System/User.ini"
    raw = user_ini.read_bytes()
    import re
    codec = "utf-16" if raw.startswith(b"\xff\xfe") else "cp1252"
    text = raw.decode(codec)
    text, count = re.subn(r"(?im)^bSubtitles=.*$", "bSubtitles=False", text)
    if count != 1:
        raise ValueError("Expected one subtitle setting in QA source")
    user_ini.write_bytes(text.encode(codec))
    before = {e["path"]: digest(target / e["path"]) for e in manifest["files"] if not e["owned"]}
    configs = {c["path"]: (target / c["path"]).read_bytes() for c in manifest["config"]}
    sentinel = target / "Save/player-progress.sentinel"
    sentinel.parent.mkdir(exist_ok=True)
    sentinel.write_bytes(b"preserve saved progress")
    results = []
    results.append(run(target, "verify", expected=1))
    # An unsupported original must fail before any resource or settings write.
    victim = target / next(iter(before))
    pristine = victim.read_bytes()
    victim.write_bytes(pristine + b"unknown-version")
    results.append(run(target, "apply", expected=1))
    victim.write_bytes(pristine)
    assert all(digest(target / p) == h for p, h in before.items())
    assert all((target / p).read_bytes() == b for p, b in configs.items())
    assert not (target / ".localization-backup/player-test/STATE.json").exists()
    results.append(run(target, "apply"))
    assert "bSubtitles=True" in user_ini.read_bytes().decode(codec)
    results.append(run(target, "verify"))
    results.append(run(target, "launch", ("-VerifyOnly",)))
    results.append(run(target, "apply"))
    results.append(run(target, "restore"))
    assert all(digest(target / p) == h for p, h in before.items())
    assert all((target / p).read_bytes() == b for p, b in configs.items())
    assert all(not (target / e["path"]).exists() for e in manifest["files"] if e["owned"])
    assert sentinel.read_bytes() == b"preserve saved progress"
    results.append(run(target, "apply"))
    results.append(run(target, "verify"))
    report.write_text(json.dumps({"results": results, "resources": len(manifest["files"]),
                                 "restored_behavior": "Original resource/config bytes restored; additions removed; saves preserved",
                                 "final_state": "Installed and verified; no game launched",
                                 "zip_sha256": digest(package)}, ensure_ascii=False, indent=2), encoding="utf-8")
    print("PLAYER PACKAGE QA PASS: original/modified/rollback/reinstall verified; no game launch")


if __name__ == "__main__":
    a=argparse.ArgumentParser(description=__doc__)
    a.add_argument("--game-dir", type=Path, required=True)
    a.add_argument("--package", type=Path, required=True)
    a.add_argument("--target", type=Path, required=True)
    a.add_argument("--report", type=Path, required=True)
    p=a.parse_args()
    qa(p.game_dir, p.package, p.target, p.report)
