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
    for name, expected in report["files"].items():
        b = (game / name).read_bytes()
        if sha(b) != expected["original_sha256"]:
            raise ValueError("Original changed")
        p = out / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(b)
    print(
        "BASELINE PASS: MenuList[2]="
        + menu(out / "System/WoT.int")
        + f"; {len(report['files'])} original hashes verified"
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
        if (out / name).read_bytes() != (game / name).read_bytes():
            raise ValueError("Rollback differs")
    print(
        "ROLLBACK PASS: MenuList[2]="
        + menu(out / "System/WoT.int")
        + f"; {len(report['files'])} originals byte-identical; modified build retained"
    )


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf8")
    p = argparse.ArgumentParser(description=__doc__)
    for name in ("game-dir", "build-dir", "out"):
        p.add_argument("--" + name, type=Path, required=True)
    a = p.parse_args()
    run(a.game_dir, a.build_dir, a.out)
