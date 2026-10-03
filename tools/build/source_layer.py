"""Optional, pinned external subtitle source; original patch baselines remain immutable."""

import hashlib
import importlib
import json
import shutil
import tempfile
from contextlib import contextmanager
from pathlib import Path
from tools.pack.ue1 import Package


def fingerprint(path, expected_hash, expected_size):
    data = path.read_bytes()
    if len(data) != expected_size or hashlib.sha256(data).hexdigest() != expected_hash:
        raise ValueError("Subtitle source/input fingerprint mismatch: " + path.name)


@contextmanager
def source_layer(game, reference, manifest):
    if reference is None:
        yield game / "System", None
        return
    fingerprint(reference, manifest["reference_sha256"], manifest["reference_size"])
    sounds = []
    for expected in manifest["package_inputs"]:
        path = (game / expected["file"]).resolve()
        if not path.is_relative_to(game.resolve()):
            raise ValueError("Invalid source package path")
        fingerprint(path, expected["sha256"], expected["size"])
        package = Package(path)
        for record in package.records():
            if record["class_name"] == "Sound":
                parts = record["path"].split(".")
                sounds.append(
                    dict(
                        section=parts[-2] if len(parts) > 1 else path.stem,
                        key=parts[-1],
                    )
                )
    with tempfile.TemporaryDirectory(prefix="wot-localization-source-") as folder:
        root = Path(folder)
        src = root / "System"
        src.mkdir()
        for path in (game / "System").glob("*.int"):
            shutil.copyfile(path, src / path.name)
        merge = importlib.import_module("tools.import.subtitle_source").prepare
        report = merge(
            game / "System" / manifest["file"],
            reference,
            root / "merged",
            {"sounds": sounds},
            manifest.get("approved_overrides", []),
            manifest.get("conflict_policy", "keep-original"),
        )
        if report["modified_sha256"] != manifest["expected_merged_sha256"]:
            raise ValueError("Merged subtitle source fingerprint mismatch")
        shutil.copyfile(root / "merged" / manifest["file"], src / manifest["file"])
        report["id"] = manifest["id"]
        yield src, report
        fingerprint(reference, manifest["reference_sha256"], manifest["reference_size"])
        for expected in manifest["package_inputs"]:
            fingerprint(game / expected["file"], expected["sha256"], expected["size"])


def load_rows(locale, config, manifest, field="subtitle_rows"):
    name = config.get(field)
    if not name:
        return []
    path = (locale / name).resolve()
    if not path.is_relative_to(locale.resolve()):
        raise ValueError("Subtitle translation path escapes locale")
    rows = json.loads(path.read_text(encoding="utf-8"))
    if any(
        r.get("source_layer") != manifest["id"] or r["file"] != manifest["file"]
        for r in rows
    ):
        raise ValueError("Subtitle translation source identity mismatch")
    return rows


def active_subtitle_texts(source, rows, files):
    from tools.extract.int_files import entries

    overrides = {
        (r["file"], r["section"], r["key"], r["occurrence"]): r["translation"]
        for r in rows
        if r.get("translation")
    }
    return [
        overrides.get((r["file"], r["section"], r["key"], r["occurrence"]), r["source"])
        for name in files
        for r in entries(source / name)
    ]


def compose_rows(base, extras, overrides, manifest):
    def identity(row):
        return (row["file"], row["section"], row["key"], row["occurrence"])

    replacements = {identity(r): r for r in overrides}
    if len(replacements) != len(overrides):
        raise ValueError("Duplicate translation override")
    allowed = {
        (manifest["file"], r["section"], r["key"], 1): r
        for r in manifest.get("approved_overrides", [])
    }
    original = {identity(r): r for r in base}
    for i, r in replacements.items():
        if i not in original or i not in allowed:
            raise ValueError("Unapproved translation override identity")
        if (
            original[i]["source_sha256"] != allowed[i]["original_source_sha256"]
            or r["source_sha256"] != allowed[i]["reference_source_sha256"]
        ):
            raise ValueError("Translation override fingerprint mismatch")
    result = [replacements.get(identity(r), r) for r in base] + extras
    if len({identity(r) for r in result}) != len(result):
        raise ValueError("Duplicate composed source identity")
    return result
