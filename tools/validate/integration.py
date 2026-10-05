"""Optional owned-game integration tests; originals are read-only inputs."""

import argparse
import json
import shutil
import sys
from pathlib import Path
from install import transaction
from src.patch.delta import sha
from tools.extract.int_files import entries


def menu(path):
    return next(
        r["source"]
        for r in entries(path)
        if r["section"] == "menuSinglePlayer" and r["key"] == "MenuList[2]"
    )


def run(game, build, out):
    game, build, out = (p.resolve() for p in (game, build, out))
    if out == game or out.is_relative_to(game) or out == build:
        raise ValueError("Use an independent test output outside original/build")
    report = json.loads((build / "BUILD_REPORT.json").read_text("utf8"))
    additions=set(json.loads((build/"PATCH.json").read_text("utf8")).get("owned_additions",[]))
    for name, expected in report["files"].items():
        if name in additions:
            if (game/name).exists():raise ValueError("Owned addition already exists")
            continue
        b = (game / name).read_bytes()
        if sha(b) != expected["original_sha256"]:
            raise ValueError("Original changed")
        p = out / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(b)
    print(
        "BASELINE PASS: MenuList[2]="
        + menu(out / "System/WoT.int")
        + f"; {len(report['files'])-len(additions)} original hashes verified; {len(additions)} additions absent"
    )
    transaction("apply", build / "PATCH.json", out)
    transaction("verify", build / "PATCH.json", out)
    for name, expected in report["files"].items():
        if (out / name).read_bytes() != (build / "resources" / name).read_bytes():
            raise ValueError("Applied bytes differ from built resource")
    print(
        "MODIFIED PASS: MenuList[2]="
        + menu(out / "System/WoT.int")
        + f"; {len(report['files'])} rebuilt resources byte-identical"
    )
    transaction("restore", build / "PATCH.json", out)
    for name in report["files"]:
        if name in additions:
            if (out/name).exists():raise ValueError("Added resource remains after rollback")
            continue
        if (out / name).read_bytes() != (game / name).read_bytes():
            raise ValueError("Rollback differs")
    print(
        "ROLLBACK PASS: MenuList[2]="
        + menu(out / "System/WoT.int")
        + f"; {len(report['files'])-len(additions)} originals byte-identical; {len(additions)} additions removed; modified build retained"
    )


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf8")
    p = argparse.ArgumentParser(description=__doc__)
    for name in ("game-dir", "build-dir", "out"):
        p.add_argument("--" + name, type=Path, required=True)
    a = p.parse_args()
    run(a.game_dir, a.build_dir, a.out)
