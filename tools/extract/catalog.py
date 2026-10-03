import collections
import csv
import json
from tools.extract.int_files import entries


def export(source, out):
    out.mkdir(parents=True, exist_ok=True)
    rows = [r for p in sorted(source.glob("*.int")) for r in entries(p)]
    (out / "strings.json").write_text(
        json.dumps(rows, ensure_ascii=False, indent=2), "utf8"
    )
    with (out / "strings.csv").open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    k: json.dumps(v, ensure_ascii=False) if isinstance(v, list) else v
                    for k, v in row.items()
                }
            )
    groups = collections.defaultdict(list)
    for r in rows:
        if r["source"]:
            groups[r["source"]].append(
                {k: r[k] for k in ("file", "section", "key", "occurrence")}
            )
    (out / "duplicates.json").write_text(
        json.dumps(
            {k: v for k, v in groups.items() if len(v) > 1},
            ensure_ascii=False,
            indent=2,
        ),
        "utf8",
    )
    print(f'EXTRACT PASS: {len(rows)} entries; {sum(r["empty"] for r in rows)} empty')
