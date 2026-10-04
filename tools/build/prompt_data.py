"""Bind localized map prompts to hash-verified, user-provided source text."""

import hashlib
import re
from tools.extract.map_messages import entries


def bind(game, data, terms=()):
    path = (game / data["source"]).resolve()
    if not path.is_relative_to(game.resolve()):
        raise ValueError("Prompt source escapes game")
    if hashlib.sha256(path.read_bytes()).hexdigest() != data["source_sha256"]:
        raise ValueError("Prompt source map fingerprint mismatch")
    originals = {(r["actor"], r["slot"]): r for r in entries(path) if r["active"]}
    identities = [(r["actor"], r["slot"]) for r in data["rows"]]
    if len(set(identities)) != len(identities) or set(identities) != set(originals):
        raise ValueError("Prompt translation must cover every active map message")
    from tools.extract.int_files import tokens
    from tools.validate.terminology import matches

    result = []
    seen_sources = {}
    for row in data["rows"]:
        source = originals[row["actor"], row["slot"]]["source"]
        target = row["translation"]
        if (
            hashlib.sha256(source.encode()).hexdigest() != row["source_sha256"]
            or not target
            or tokens(source) != tokens(target)
            or any(c in source + target for c in '"\r\n\0')
        ):
            raise ValueError("Invalid prompt source, syntax or placeholders")
        if any(t not in target for _, t in matches(source, terms)):
            raise ValueError("Prompt glossary mismatch: " + row["actor"])
        key_pattern = r"(?<![A-Za-z0-9])(?:F\d+|\d+)(?![A-Za-z0-9])"
        if re.findall(key_pattern, source) != re.findall(key_pattern, target):
            raise ValueError("Prompt key/number mismatch")
        if source.startswith(" //") and not target.startswith(" //"):
            raise ValueError("Preserve existing comment-like display prefix")
        if source in seen_sources and seen_sources[source] != target:
            raise ValueError("Identical runtime prompt has conflicting translations")
        seen_sources[source] = target
        result.append(dict(source=source, translation=target))
    if len(result) > 128:
        raise ValueError("Prompt runtime capacity exceeded")
    return result
