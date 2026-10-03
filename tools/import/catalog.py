"""Convert an extracted CSV/JSON table to the source-hash translation schema."""

import argparse
import csv
import hashlib
import json
from pathlib import Path


def convert(source, output):
    if source.resolve() == output.resolve():
        raise ValueError("Conversion output must differ from source")
    if source.suffix.lower() == ".csv":
        with source.open(encoding="utf-8-sig", newline="") as f:
            rows = list(csv.DictReader(f))
        for row in rows:
            row["tokens"] = json.loads(row["tokens"])
    else:
        rows = json.loads(source.read_text("utf8"))
    result = []
    for row in rows:
        if row.get("kind") == "structured-metadata":
            continue
        result.append(
            {k: row[k] for k in ("file", "section", "key", "translation", "tokens")}
            | {
                "occurrence": int(row["occurrence"]),
                "source_sha256": hashlib.sha256(row["source"].encode()).hexdigest(),
                "source_length": len(row["source"]),
                "status": "draft",
            }
        )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2), "utf8")
    print(f"CONVERT PASS: {len(result)} entries")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("source", type=Path)
    p.add_argument("output", type=Path)
    a = p.parse_args()
    convert(a.source, a.output)
