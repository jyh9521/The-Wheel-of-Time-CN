"""Snapshot or compare a workspace without modifying anything within it."""

import argparse
import hashlib
import json
from pathlib import Path


def snapshot(root):
    root = Path(root).resolve(strict=True)
    if not root.is_dir():
        raise ValueError("Inventory root must be a directory")
    result = []
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise ValueError("Inventory does not follow symbolic links: " + str(path))
        if not path.is_file():
            continue
        before = path.stat()
        digest = hashlib.sha256()
        with path.open("rb") as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(block)
        after = path.stat()
        if (before.st_size, before.st_mtime_ns) != (
            after.st_size,
            after.st_mtime_ns,
        ):
            raise ValueError("File changed during inventory: " + str(path))
        result.append(
            {
                "path": path.relative_to(root).as_posix(),
                "size": after.st_size,
                "mtime_ns": after.st_mtime_ns,
                "sha256": digest.hexdigest(),
            }
        )
    return result


def compare(before, after):
    def index(rows):
        result = {}
        for row in rows:
            if row["path"] in result:
                raise ValueError("Duplicate inventory path: " + row["path"])
            result[row["path"]] = (row["size"], row["mtime_ns"], row["sha256"])
        return result

    a, b = index(before), index(after)
    return {
        "added": sorted(b.keys() - a.keys()),
        "removed": sorted(a.keys() - b.keys()),
        "changed": sorted(p for p in a.keys() & b.keys() if a[p] != b[p]),
    }


def run(root, output, baseline=None):
    root, output = Path(root).resolve(strict=True), Path(output).resolve()
    if output.is_relative_to(root):
        raise ValueError("Audit output must be outside the audited workspace")
    rows = snapshot(root)
    if baseline:
        delta = compare(json.loads(Path(baseline).read_text("utf8")), rows)
        if any(delta.values()):
            raise ValueError("Workspace differs: " + json.dumps(delta))
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(rows, indent=2) + "\n", encoding="utf8")
    print(
        f"AUDIT PASS: {len(rows)} files; " + ("unchanged" if baseline else "snapshot")
    )
    return rows


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--compare", type=Path)
    args = parser.parse_args()
    run(args.root, args.out, args.compare)
