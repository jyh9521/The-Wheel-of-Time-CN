"""Package a locally built developer preview; no complete game resources or fonts."""

import argparse
import hashlib
import json
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def package(build_dir, output, notes):
    build_dir, output = build_dir.resolve(), output.resolve()
    report = json.loads((build_dir / "BUILD_REPORT.json").read_text(encoding="utf-8"))
    bundle = json.loads((build_dir / "PATCH.json").read_text(encoding="utf-8"))
    if set(bundle["files"]) != set(report["files"]):
        raise ValueError("Build manifest mismatch")
    for name, d in bundle["files"].items():
        if d["modified_sha256"] != report["files"][name]["modified_sha256"]:
            raise ValueError("Patch hash mismatch")
        resource = (build_dir / "resources" / name).resolve()
        if not resource.is_relative_to((build_dir / "resources").resolve()):
            raise ValueError("Resource path escapes build")
        data = resource.read_bytes()
        if (
            len(data) != d["modified_size"]
            or hashlib.sha256(data).hexdigest() != d["modified_sha256"]
        ):
            raise ValueError("Resource fingerprint mismatch")
    files = {
        "PATCH.json": (build_dir / "PATCH.json").read_bytes(),
        "BUILD_REPORT.json": (build_dir / "BUILD_REPORT.json").read_bytes(),
        "TESTING.md": notes.read_bytes(),
    }
    for name in [
        "install.py",
        "src/__init__.py",
        "src/patch/__init__.py",
        "src/patch/delta.py",
        "LICENSE",
        "LICENSE-translations.md",
    ]:
        files[name] = (ROOT / name).read_bytes()
    files["Manage-Patch.ps1"] = (
        ROOT / "assets/templates/manage-preview.ps1"
    ).read_bytes()
    checklist = notes.with_suffix(".json")
    if checklist.exists():
        files[checklist.name] = checklist.read_bytes()
    files["CONTENTS.json"] = (
        json.dumps(
            {n: hashlib.sha256(b).hexdigest() for n, b in files.items()}, indent=2
        )
        + "\n"
    ).encode()
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, data in sorted(files.items()):
            info = zipfile.ZipInfo(name, date_time=(2020, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, data)
    with zipfile.ZipFile(output) as archive:
        if archive.testzip() is not None:
            raise ValueError("Preview ZIP CRC mismatch")
        for name, data in files.items():
            if archive.read(name) != data:
                raise ValueError("Preview ZIP readback mismatch")
    print(
        f"PREVIEW PACKAGE PASS: {len(files)} files; ZIP CRC/readback verified; {output}"
    )
    return output


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--build-dir", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--notes", type=Path, required=True)
    a = p.parse_args()
    package(a.build_dir, a.out, a.notes)
