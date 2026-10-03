"""Read-only subtitle/Sound inventory; static associations are not runtime coverage."""

import argparse
import collections
import hashlib
import json
from pathlib import Path
from tools.extract.int_files import entries
from tools.pack.ue1 import Package


def key(section, name):
    return (section.casefold(), name.casefold())


def index(rows):
    result = {}
    for row in rows:
        identity = key(row["section"], row["key"])
        if identity in result:
            raise ValueError("Ambiguous subtitle identity: " + str(identity))
        result[identity] = row
    return result


def correlate(rows, sounds, maps, translations):
    table = index(rows)
    translated = index(
        [r for r in translations if r["file"].casefold() == "wotsubtitles.int"]
    )
    references = collections.defaultdict(set)
    for map_name, paths in maps.items():
        for path in paths:
            references[path.casefold()].add(map_name)
    records = []
    used = set()
    for sound in sounds:
        identity = key(sound["section"], sound["key"])
        row = table.get(identity)
        used.add(identity)
        translation = translated.get(identity, {})
        records.append(
            dict(
                sound,
                subtitle_state=(
                    "missing-key"
                    if row is None
                    else "empty" if row["empty"] else "text"
                ),
                source_length=len(row["source"]) if row else 0,
                translation_state=(
                    "translated" if translation.get("translation") else "pending"
                ),
                maps=sorted(references[sound["sound"].casefold()]),
                runtime_verified=False,
            )
        )
    return dict(
        sounds=records,
        counts=dict(collections.Counter(r["subtitle_state"] for r in records)),
        orphan_subtitle_keys=[
            dict(section=r["section"], key=r["key"])
            for k, r in table.items()
            if k not in used
        ],
        disclaimer="Sound imports indicate static association, not event order or proof of playback. Empty effects/grunts are not automatically missing dialogue. Movies are separate.",
    )


def audit(game, out, locale_file=None, reference_files=()):
    game, out = game.resolve(), out.resolve()
    if out == game or out.is_relative_to(game):
        raise ValueError("Output must be outside the game directory")
    originals = {}

    def track(path):
        data = path.read_bytes()
        originals[path] = hashlib.sha256(data).hexdigest()
        return dict(
            file=path.relative_to(game).as_posix(),
            size=len(data),
            sha256=originals[path],
        )

    subtitle = game / "System/WoTsubtitles.int"
    inputs = [track(subtitle)]
    rows = entries(subtitle)
    sounds, maps = [], {}
    for folder, pattern in [("Sounds", "*.uax"), ("System", "*.u")]:
        for path in sorted((game / folder).glob(pattern)):
            inputs.append(track(path))
            package = Package(path)
            for record in package.records():
                if record["class_name"] == "Sound":
                    object_path = path.stem + "." + record["path"]
                    parts = object_path.split(".")
                    sounds.append(
                        dict(
                            sound=object_path,
                            section=parts[-2],
                            key=parts[-1],
                            file=path.relative_to(game).as_posix(),
                            export=record["index"],
                        )
                    )
    for path in sorted((game / "Maps").glob("*.wot")):
        inputs.append(track(path))
        package = Package(path)
        maps[path.name] = [
            package.full(-i - 1)
            for i, imp in enumerate(package.imports)
            if package.names[imp["cn"]] == "Sound"
        ]
    translations = (
        json.loads(locale_file.read_text(encoding="utf-8")) if locale_file else []
    )
    report = correlate(rows, sounds, maps, translations)
    report["inputs"] = inputs
    report["subtitle_entries"] = len(rows)
    report["subtitle_empty"] = sum(r["empty"] for r in rows)
    report["reference_comparisons"] = []
    for path in reference_files:
        ref = index(entries(path))
        report["reference_comparisons"].append(
            dict(
                file=path.name,
                sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                total=len(ref),
                nonempty=sum(not r["empty"] for r in ref.values()),
                matches=sum(key(r["section"], r["key"]) in ref for r in rows),
                recoverable_candidates=[
                    dict(section=r["section"], key=r["key"])
                    for r in rows
                    if r["empty"]
                    and ref.get(key(r["section"], r["key"]), {}).get("source")
                ],
                provenance_verified=False,
            )
        )
    for path, digest in originals.items():
        if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            raise ValueError("Read-only input changed: " + str(path))
    out.mkdir(parents=True, exist_ok=True)
    target = out / "COVERAGE.json"
    target.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    assert json.loads(target.read_text(encoding="utf-8")) == report
    print(
        f"COVERAGE PASS: {len(rows)} keys; {report['subtitle_empty']} empty; {len(sounds)} Sound exports; {len(maps)} maps; {len(originals)} inputs unchanged"
    )
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--game-dir", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--strings", type=Path)
    parser.add_argument("--reference", type=Path, action="append", default=[])
    args = parser.parse_args()
    audit(args.game_dir, args.out, args.strings, args.reference)


if __name__ == "__main__":
    main()
