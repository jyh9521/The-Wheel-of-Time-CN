"""Hash-gated UE1 Preferences display subfields; preserve structural identifiers."""

import collections
import hashlib
import importlib
import re
from pathlib import Path
from tools.extract.int_files import entries, decode, encode, tokens

FIELDS = re.compile(r'([A-Za-z_]\w*)=(?:"([^"\\]*)"|([^,()]*))(?:,|$)')


def fields(value):
    if not value.startswith("(") or not value.endswith(")"):
        raise ValueError("Invalid Preferences structure")
    interior = value[1:-1]
    found = list(FIELDS.finditer(interior))
    if not found or "".join(m.group() for m in found) != interior:
        raise ValueError("Unsupported Preferences field syntax")
    if len({m[1] for m in found}) != len(found):
        raise ValueError("Duplicate Preferences field")
    return {m[1]: m[2] if m[2] is not None else m[3] for m in found}


def replace_display(value, translations):
    original = fields(value)
    if not translations or set(translations) - {"Caption", "Parent"}:
        raise ValueError("Only Caption/Parent display fields may change")
    for key, text in translations.items():
        if key not in original or not text or any(c in text for c in '"\\\r\n\0(),='):
            raise ValueError("Invalid display translation")
        if tokens(original[key]) != tokens(text):
            raise ValueError("Display control mismatch")

    def repl(m):
        key = m[1]
        if key not in translations:
            return m.group()
        return (
            key
            + '="'
            + translations[key]
            + '"'
            + ("," if m.group().endswith(",") else "")
        )

    result = "(" + FIELDS.sub(repl, value[1:-1]) + ")"
    rebuilt = fields(result)
    if any(rebuilt[k] != v for k, v in original.items() if k not in translations):
        raise ValueError("Structural metadata changed")
    return result


def build(src, dst, spec, config, profile):
    src, dst = Path(src).resolve(), Path(dst).resolve()
    if src == dst:
        raise ValueError("Output must differ from source")
    grouped = collections.defaultdict(list)
    identities = set()
    for row in spec["preferences"]:
        name = row["file"]
        if (
            Path(name).name != name
            or any(c in name for c in "/\\:")
            or not name.endswith(".int")
        ):
            raise ValueError("Invalid resource filename")
        if "System/" + name not in profile["files"]:
            raise ValueError("Resource not in original profile")
        identity = (name, row["section"], row["key"], row["occurrence"])
        if (
            identity in identities
            or row["section"] != "Public"
            or row["key"] != "Preferences"
        ):
            raise ValueError("Invalid or duplicate Preferences identity")
        identities.add(identity)
        grouped[name].append(row)
    # Preflight all fields before writing even one resource.
    for name, rows in grouped.items():
        actual = {
            (r["section"], r["key"], r["occurrence"]): r for r in entries(src / name)
        }
        for row in rows:
            r = actual[(row["section"], row["key"], row["occurrence"])]
            if hashlib.sha256(r["source"].encode()).hexdigest() != row["source_sha256"]:
                raise ValueError("Preferences source fingerprint differs")
            replace_display(r["source"], row["translations"])
    importer = importlib.import_module("tools.import.int_files")
    importer.import_rows(src, spec["strings"], dst, config, profile, preserve_existing=True)
    changes = []
    for name, rows in grouped.items():
        output = dst / name
        if output.is_symlink() or not output.resolve().is_relative_to(dst):
            raise ValueError("Output escapes destination")
        original = src / name
        source_data = original.read_bytes()
        text, _ = decode(output.read_bytes() if output.exists() else source_data)
        lines = text.splitlines(keepends=True)
        actual = {
            (r["section"], r["key"], r["occurrence"]): r
            for r in entries(output if output.exists() else original)
        }
        for row in rows:
            r = actual[(row["section"], row["key"], row["occurrence"])]
            index = r["line"] - 1
            line = lines[index]
            ending = (
                "\r\n" if line.endswith("\r\n") else "\n" if line.endswith("\n") else ""
            )
            lines[index] = (
                line.split("=", 1)[0]
                + "="
                + replace_display(r["source"], row["translations"])
                + ending
            )
            changes.append(
                {
                    "file": name,
                    "occurrence": row["occurrence"],
                    "fields": row["translations"],
                }
            )
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(encode("".join(lines), config["encoding"]))
        if original.read_bytes() != source_data:
            raise ValueError("Source changed")
    names = sorted(set(grouped) | {r["file"] for r in spec["strings"]})
    print(
        f"NATIVE UI PASS: {len(changes)} Preferences rows; {len(spec['strings'])} strings; {len(names)} files; structural fields and source unchanged"
    )
    return {
        "files": names,
        "preferences": changes,
        "strings": len(spec["strings"]),
        "scope": "Titles, registered preference captions/parents and native window buttons; raw property/category identifiers unchanged",
    }
