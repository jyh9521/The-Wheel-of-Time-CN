"""Verify native UI display edits against unmodified .int source and tree links."""

import argparse
import hashlib
import importlib
import json
from pathlib import Path
from tools.extract.int_files import entries

module = importlib.import_module("tools.import.preferences")


def verify(source, spec, baseline=None):
    prefs = {
        (r["file"], r["section"], r["key"], r["occurrence"]): r
        for r in spec["preferences"]
    }
    strings = {
        (r["file"], r["section"], r["key"], r["occurrence"]): r for r in spec["strings"]
    }
    names = sorted({i[0] for i in prefs} | {i[0] for i in strings})
    nodes = []
    root = None
    for name in names:
        actual = {
            (r["file"], r["section"], r["key"], r["occurrence"]): r
            for r in entries(source / name)
        }
        original = {
            (r["file"], r["section"], r["key"], r["occurrence"]): r
            for r in entries((baseline or source) / name)
        }
        if set(actual) != set(original):
            raise ValueError("Resource identities changed")
        for identity, old in original.items():
            new = actual[identity]["source"]
            row = prefs.get(identity) or strings.get(identity)
            if (
                row
                and hashlib.sha256(old["source"].encode()).hexdigest()
                != row["source_sha256"]
            ):
                raise ValueError("Original identity fingerprint differs")
            expected = old["source"]
            if baseline:
                if identity in prefs:
                    expected = module.replace_display(expected, row["translations"])
                elif identity in strings:
                    expected = row["translation"]
            if new != expected:
                raise ValueError("Unexpected entry edit: " + str(identity))
            if identity in prefs:
                nodes.append(module.fields(new))
            if name == "Window.int" and identity[1:3] == (
                "General",
                "AdvancedOptionsTitle",
            ):
                root = new
    captions = {n["Caption"] for n in nodes}
    if root is None or any(n["Parent"] not in captions | {root} for n in nodes):
        raise ValueError("Preference tree has disconnected parents")
    mode = "MODIFIED" if baseline else "BASELINE"
    print(
        f"NATIVE UI {mode} PASS: {len(prefs)} Preferences rows; {len(strings)} strings; {len(names)} files; tree connected; other entries and structural fields unchanged"
    )


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source", type=Path, required=True)
    p.add_argument("--locale-data", type=Path, required=True)
    p.add_argument("--baseline", type=Path)
    a = p.parse_args()
    verify(a.source, json.loads(a.locale_data.read_text("utf8")), a.baseline)
