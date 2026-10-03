"""Read the sole Markdown terminology source; never maintain a parallel term map."""

import re
import hashlib
from pathlib import Path
from tools.extract.int_files import entries, tokens, translation_tokens


def normalize(text):
    return text.replace("’", "'").replace("‘", "'").casefold()


def load_terms(path, target_column):
    text = Path(path).read_text(encoding="utf-8")
    tables = re.findall(r"(?m)(?:^\|[^\n]*\n)+", text)
    selected = []
    for table in tables:
        lines = table.splitlines()
        headers = [c.strip() for c in lines[0].strip().strip("|").split("|")]
        if "English" in headers and target_column in headers:
            selected.append((lines, headers))
    if len(selected) != 1:
        raise ValueError("Expected exactly one confirmed terminology table")
    lines, headers = selected[0]
    source_index, target_index = headers.index("English"), headers.index(target_column)
    terms = []
    seen = set()
    for line in lines[2:]:
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) != len(headers):
            raise ValueError("Malformed terminology row")
        source, target = cells[source_index].strip("*`"), cells[target_index].strip(
            "*`"
        )
        if not source or not target or normalize(source) in seen:
            raise ValueError("Empty or duplicate confirmed terminology")
        seen.add(normalize(source))
        terms.append((source, target))
    if not terms:
        raise ValueError("Empty confirmed terminology table")
    return terms


def matches(source, terms):
    # Protected identifiers are not prose. Remove only from the temporary matcher.
    for token in tokens(source):
        source = source.replace(token, " ")
    source = normalize(source)
    occupied, found = set(), []
    for english, target in sorted(terms, key=lambda t: len(t[0]), reverse=True):
        pattern = r"(?<![\w'])" + re.escape(normalize(english)) + r"(?:s|es)?(?![\w'])"
        for match in re.finditer(pattern, source):
            span = set(range(match.start(), match.end()))
            if span & occupied:
                continue
            occupied |= span
            found.append((english, target))
    return list(dict.fromkeys(found))


def load_exceptions(path):
    text = Path(path).read_text(encoding="utf-8")
    lines = []
    for table in re.findall(r"(?m)(?:^\|[^\n]*\n)+", text):
        candidate = table.splitlines()
        headers = [c.strip() for c in candidate[0].strip().strip("|").split("|")]
        if headers == [
            "File",
            "Section",
            "Key",
            "Occurrence",
            "Term",
            "Source SHA256",
            "Reason",
        ]:
            if lines:
                raise ValueError("Duplicate terminology exception table")
            lines = candidate
    result = []
    for line in lines[2:]:
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) != 7 or len(cells[5]) != 64 or not cells[6]:
            raise ValueError("Malformed terminology context exception")
        result.append(
            dict(
                identity=(cells[0], cells[1], cells[2], int(cells[3])),
                term=cells[4],
                source_sha256=cells[5],
                reason=cells[6],
            )
        )
    if len({(r["identity"], normalize(r["term"])) for r in result}) != len(result):
        raise ValueError("Duplicate terminology context exception")
    return result


def audit(rows, source_dir, terms, exceptions=()):
    sources, findings, checked, hits = {}, [], 0, 0
    for row in rows:
        if not row.get("translation"):
            continue
        checked += 1
        name = row["file"]
        if name not in sources:
            sources[name] = {
                (r["section"], r["key"], r["occurrence"]): r["source"]
                for r in entries(Path(source_dir) / name)
            }
        identity = (row["section"], row["key"], int(row["occurrence"]))
        source = sources[name][identity]
        for english, target in matches(source, terms):
            exempt = [
                e
                for e in exceptions
                if e["identity"] == (name, *identity)
                and normalize(e["term"]) == normalize(english)
            ]
            if exempt:
                if (
                    hashlib.sha256(source.encode("utf-8")).hexdigest()
                    != exempt[0]["source_sha256"]
                ):
                    raise ValueError("Terminology context exception source changed")
                continue
            hits += 1
            if target not in row["translation"]:
                findings.append(
                    dict(
                        file=name,
                        section=row["section"],
                        key=row["key"],
                        occurrence=row["occurrence"],
                        term=english,
                        expected=target,
                    )
                )
    return dict(translated_rows=checked, term_matches=hits, findings=findings)


def validate(rows, source_dir, glossary, target_column):
    result = audit(
        rows, source_dir, load_terms(glossary, target_column), load_exceptions(glossary)
    )
    if result["findings"]:
        raise ValueError("Terminology mismatch: " + repr(result["findings"]))
    print(
        f"TERMINOLOGY PASS: {result['translated_rows']} translated rows; {result['term_matches']} confirmed term matches; GLOSSARY.md source"
    )
    return result


def main():
    import argparse
    import importlib
    import json

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--glossary", type=Path, required=True)
    parser.add_argument("--target-column", required=True)
    parser.add_argument("--source-dir", type=Path, required=True)
    parser.add_argument("--catalog", type=Path, nargs="+", required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    terms, exceptions = load_terms(args.glossary, args.target_column), load_exceptions(
        args.glossary
    )
    importer = importlib.import_module("tools.import.int_files")
    results = []
    for path in args.catalog:
        rows = json.loads(path.read_text("utf8"))
        importer.verify_sources(args.source_dir, rows)
        for r in rows:
            if r.get("translation") and translation_tokens(r) != r["tokens"]:
                raise ValueError(
                    "Protected tokens changed: "
                    + repr((r["file"], r["section"], r["key"]))
                )
        results.append(
            dict(catalog=str(path), **audit(rows, args.source_dir, terms, exceptions))
        )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(results, ensure_ascii=False, indent=2) + "\n", "utf8"
    )
    assert json.loads(args.out.read_text("utf8")) == results
    failures = sum(len(r["findings"]) for r in results)
    print(
        f"TERMINOLOGY AUDIT: {sum(r['translated_rows'] for r in results)} translated rows; {failures} mismatches; sources and protected tokens verified"
    )
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
