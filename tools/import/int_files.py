"""Key/occurrence-addressed import with mandatory source and control checks."""

import collections, hashlib
from pathlib import Path
from tools.extract.int_files import entries, decode, encode, tokens, translation_tokens


def validate_rows(rows, config):
    seen = set()
    pending = 0
    groups = {}
    for r in rows:
        name = r["file"]
        if (
            Path(name).name != name
            or "/" in name
            or "\\" in name
            or ":" in name
            or not name.lower().endswith(".int")
        ):
            raise ValueError("Invalid resource filename")
        identity = (name.lower(), r["section"], r["key"], int(r["occurrence"]))
        if identity in seen:
            raise ValueError("Duplicate ID: " + repr(identity))
        seen.add(identity)
        s = r.get("translation", "")
        if not s:
            pending += 1
            continue
        if translation_tokens(r) != r["tokens"]:
            raise ValueError("Placeholder/control mismatch: " + repr(identity))
        if any(c in s for c in ['"', "\n", "\r", "\0"]) or any(
            0xD800 <= ord(c) <= 0xDFFF or ord(c) > 0xFFFF for c in s
        ):
            raise ValueError("Unsupported syntax or non-BMP character")
        if len(s) > r.get("max_characters", config["validation"]["max_characters"]):
            raise ValueError("Character limit exceeded")
        payload = encode(s, config["encoding"])
        if "max_bytes" in r and len(payload) > r["max_bytes"]:
            raise ValueError("Encoded byte limit exceeded (including BOM)")
        if r.get("sync_group"):
            group = r["sync_group"]
            if group in groups and groups[group] != s:
                raise ValueError("Associated translation mismatch: " + group)
            groups[group] = s
    return pending


def verify_sources(src, rows):
    """Read-only source preflight for every ID, including untranslated rows."""
    sources = {}
    for row in rows:
        name = row["file"]
        if name not in sources:
            sources[name] = {
                (a["section"], a["key"], a["occurrence"]): a
                for a in entries(Path(src) / name)
            }
        identity = (row["section"], row["key"], int(row["occurrence"]))
        if identity not in sources[name]:
            raise ValueError("Source ID missing: " + repr((name, *identity)))
        actual = sources[name][identity]
        if (
            hashlib.sha256(actual["source"].encode()).hexdigest()
            != row["source_sha256"]
        ):
            raise ValueError("Source changed: " + repr((name, *identity)))
        if tokens(actual["source"]) != row["tokens"]:
            raise ValueError(
                "Source token metadata differs: " + repr((name, *identity))
            )
        if row.get("literal_token_translations"):
            if actual["source"].count("@") != row.get("markup_delimiter_count"):
                raise ValueError("Source markup delimiter metadata differs")
            for mapping in row["literal_token_translations"]:
                if actual["source"].count(mapping["source"]) != row["tokens"].count(
                    mapping["source"]
                ):
                    raise ValueError("Literal source span metadata differs")
            translation_tokens(row)
        if len(actual["source"]) != row["source_length"]:
            raise ValueError(
                "Source length metadata differs: " + repr((name, *identity))
            )
        if row.get("translation") and actual["kind"] == "structured-metadata":
            raise ValueError("Structured metadata requires a subfield importer")
    return len(rows)


def import_rows(src, rows, dst, config, profile, preserve_existing=False):
    validate_rows(rows, config)
    src = Path(src).resolve()
    dst = Path(dst).resolve()
    if dst == src:
        raise ValueError("Output must differ from original")
    verify_sources(src, rows)
    grouped = collections.defaultdict(list)
    for r in rows:
        if r.get("translation"):
            grouped[r["file"]].append(r)
    reports = []
    for name, rs in sorted(grouped.items()):
        p = src / name
        target = (dst / name).resolve()
        if target == p.resolve() or not target.is_relative_to(dst):
            raise ValueError("Output symlink escapes destination")
        base = target if preserve_existing and target.exists() else p
        t, _ = decode(base.read_bytes())
        lines = t.splitlines(keepends=True)
        current = {(r["section"], r["key"], r["occurrence"]): r for r in entries(p)}
        output_ids = {(r['section'], r['key'], r['occurrence']): r for r in entries(base)}
        for r in rs:
            a = current[(r["section"], r["key"], int(r["occurrence"]))]
            if a["kind"] == "structured-metadata":
                raise ValueError("Structured metadata requires a subfield importer")
            if (
                hashlib.sha256(a["source"].encode()).hexdigest() != r["source_sha256"]
                or tokens(a["source"]) != r["tokens"]
            ):
                raise ValueError("Source changed")
            v = r["translation"]
            padding = 0
            if (
                name in profile["subtitle_files"]
                and config["subtitle_timing"] == "preserve-source-length"
            ):
                padding = max(0, len(a["source"]) - len(v))
            i = output_ids[(r['section'], r['key'], int(r['occurrence']))]['line'] - 1
            line = lines[i]
            end = (
                "\r\n" if line.endswith("\r\n") else "\n" if line.endswith("\n") else ""
            )
            v = v + " " * padding
            quote = a["quoted"] or padding > 0
            lines[i] = (
                line.split("=", 1)[0] + "=" + ('"' + v + '"' if quote else v) + end
            )
            reports.append(
                {
                    "file": name,
                    "section": r["section"],
                    "key": r["key"],
                    "padding": padding,
                }
            )
        dst.mkdir(parents=True, exist_ok=True)
        target = (dst / name).resolve()
        if target == p.resolve() or not target.is_relative_to(dst):
            raise ValueError("Output symlink escapes destination")
        target.write_bytes(encode("".join(lines), config["encoding"]))
    return reports
