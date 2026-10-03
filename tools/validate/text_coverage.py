"""Audit source coverage separately from nonempty translations and semantic QA."""

import argparse
import hashlib
import json
from pathlib import Path
from tools.extract.int_files import entries

ROOT = Path(__file__).resolve().parents[2]


def identity(row):
    return tuple(row[k] for k in ("file", "section", "key", "occurrence"))


def audit(rows, source_dir, policy):
    translations = {identity(r): r for r in rows}
    if len(translations) != len(rows):
        raise ValueError("Duplicate translation identity")
    preserved = {identity(r): r for r in policy["preserved_entries"]}
    if len(preserved) != len(policy["preserved_entries"]):
        raise ValueError("Duplicate preserved identity")
    missing, passthrough, matched = [], [], set()
    counts = dict(source_nonempty=0, populated=0, preserved=0, source_empty=0)
    for name in policy["files"]:
        for row in entries(Path(source_dir) / name):
            if row["kind"] != "string-candidate":
                continue
            if not row["source"]:
                counts["source_empty"] += 1
                continue
            counts["source_nonempty"] += 1
            key = identity(row)
            digest = hashlib.sha256(row["source"].encode("utf8")).hexdigest()
            translated = translations.get(key)
            if key in preserved:
                rule = preserved[key]
                if digest != rule["source_sha256"] or translated:
                    raise ValueError(
                        "Preserved entry changed or translated: " + repr(key)
                    )
                matched.add(key)
                counts["preserved"] += 1
            elif translated and translated.get("translation"):
                if digest != translated["source_sha256"]:
                    raise ValueError("Translation source changed: " + repr(key))
                counts["populated"] += 1
                if translated["translation"] == row["source"]:
                    passthrough.append(list(key))
            else:
                missing.append(list(key))
    if matched != set(preserved):
        raise ValueError("Preserved entry missing from source")
    return dict(
        **counts,
        missing=missing,
        source_equal=passthrough,
        semantic_review_complete=False,
        in_game_coverage_verified=False,
    )


def main():
    from tools.build.source_layer import source_layer, load_rows, compose_rows

    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--locale", default="zh-CN")
    p.add_argument("--game-dir", type=Path, required=True)
    p.add_argument("--subtitle-source", type=Path)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    locale = (ROOT / "locales" / args.locale).resolve()
    if locale.parent != (ROOT / "locales").resolve():
        raise ValueError("Invalid locale")
    config = json.loads((locale / "config.json").read_text("utf8"))
    rows = json.loads((locale / "strings.json").read_text("utf8"))
    manifest = (
        json.loads((ROOT / "profiles/subtitle-source.json").read_text("utf8"))
        if args.subtitle_source
        else {}
    )
    if args.subtitle_source:
        rows = compose_rows(
            rows,
            load_rows(locale, config, manifest),
            load_rows(locale, config, manifest, "subtitle_overrides"),
            manifest,
        )
    with source_layer(args.game_dir, args.subtitle_source, manifest) as (sources, _):
        report = audit(
            rows,
            sources,
            json.loads((ROOT / "profiles/text-coverage.json").read_text("utf8")),
        )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", "utf8")
    print(
        f"TEXT COVERAGE: {report['populated']} populated; {report['preserved']} preserved; {len(report['missing'])} missing; {len(report['source_equal'])} source-equal; semantic/in-game acceptance pending"
    )
    return 1 if report["missing"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
