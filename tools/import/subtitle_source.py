"""Merge user-supplied subtitle sources into a separate research copy only."""

import argparse
import hashlib
import json
from pathlib import Path
from tools.extract.int_files import decode, encode, entries
from tools.validate.subtitle_coverage import index, key


def prepare(original, reference, out, inventory):
    original, reference, out = (Path(p).resolve() for p in (original, reference, out))
    if any(out == p or out.is_relative_to(p.parent) for p in (original, reference)):
        raise ValueError("Use an independent output directory")
    raw, supplied = original.read_bytes(), reference.read_bytes()
    baseline, additions = index(entries(original)), index(entries(reference))
    sounds = {key(r["section"], r["key"]) for r in inventory["sounds"]}
    text, encoding = decode(raw)
    lines = text.splitlines(keepends=True)
    changes, conflicts, unsupported = [], [], []
    for identity, row in additions.items():
        previous = baseline.get(identity)
        if previous and not previous["empty"]:
            if row["source"] != previous["source"]:
                conflicts.append(
                    dict(
                        section=row["section"],
                        key=row["key"],
                        resolution="keep-original",
                    )
                )
            continue
        if row["empty"]:
            continue
        if identity not in sounds:
            unsupported.append(dict(section=row["section"], key=row["key"]))
            continue
        value = row["source"]
        if any(c in value for c in ['"', "\r", "\n", "\0"]):
            raise ValueError("Unsupported subtitle source syntax")
        if previous:
            n = previous["line"] - 1
            line = lines[n]
            ending = (
                "\r\n" if line.endswith("\r\n") else "\n" if line.endswith("\n") else ""
            )
            lines[n] = line.split("=", 1)[0] + '="' + value + '"' + ending
        else:
            lines.append(
                "\r\n[" + row["section"] + "]\r\n" + row["key"] + '="' + value + '"\r\n'
            )
        changes.append(
            dict(
                section=row["section"],
                key=row["key"],
                action="fill-empty" if previous else "add-key",
                source_sha256=hashlib.sha256(value.encode("utf-8")).hexdigest(),
            )
        )
    payload = encode("".join(lines), encoding)
    out.mkdir(parents=True, exist_ok=True)
    target = out / "WoTsubtitles.int"
    target.write_bytes(payload)
    actual = index(entries(target))
    for identity, row in baseline.items():
        if not row["empty"]:
            assert actual[identity]["source"] == row["source"]
    for change in changes:
        identity = key(change["section"], change["key"])
        assert actual[identity]["source"] == additions[identity]["source"]
    assert baseline.keys() <= actual.keys()
    assert original.read_bytes() == raw and reference.read_bytes() == supplied
    report = dict(
        original_sha256=hashlib.sha256(raw).hexdigest(),
        reference_sha256=hashlib.sha256(supplied).hexdigest(),
        modified_sha256=hashlib.sha256(payload).hexdigest(),
        changes=changes,
        conflicts=conflicts,
        unsupported=unsupported,
        retained_omitted_keys=[
            dict(section=r["section"], key=r["key"])
            for k, r in baseline.items()
            if k not in additions
        ],
        total=len(actual),
        nonempty=sum(not r["empty"] for r in actual.values()),
        runtime_verified=False,
        production_build_integrated=False,
    )
    (out / "DIFF.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    assert json.loads((out / "DIFF.json").read_text(encoding="utf-8")) == report
    print(
        f"SOURCE MERGE PASS: {len(changes)} fills/additions; {len(conflicts)} conflicts preserved; {report['total']} keys; {report['nonempty']} nonempty; inputs unchanged"
    )
    return report


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--original", type=Path, required=True)
    p.add_argument("--reference", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--inventory", type=Path, required=True)
    a = p.parse_args()
    prepare(
        a.original,
        a.reference,
        a.out,
        json.loads(a.inventory.read_text(encoding="utf-8")),
    )


if __name__ == "__main__":
    main()
