import re, collections


def decode(b):
    if b.startswith(b"\xff\xfe"):
        return b[2:].decode("utf-16le"), "utf-16le-bom"
    if b.startswith(b"\xfe\xff"):
        return b[2:].decode("utf-16be"), "utf-16be-bom"
    if b.startswith(b"\xef\xbb\xbf"):
        return b[3:].decode("utf8"), "utf-8-bom"
    try:
        return b.decode("ascii"), "ascii"
    except UnicodeDecodeError:
        return b.decode("cp1252"), "cp1252-assumed"


def encode(t, e):
    if e == "utf-16le-bom":
        return b"\xff\xfe" + t.encode("utf-16le")
    if e == "utf-16be-bom":
        return b"\xfe\xff" + t.encode("utf-16be")
    if e == "utf-8-bom":
        return b"\xef\xbb\xbf" + t.encode("utf8")
    return t.encode("ascii" if e == "ascii" else "cp1252")


def tokens(s):
    # Preserve known forms and conservatively retain unknown %-prefixed codes.
    return re.findall(
        r"@[A-Za-z_][\w .]*@|%[A-Za-z_][A-Za-z0-9_=]*|%\d*\.?\d*[sdif]|%[^\s%]+|\{[^{}]+\}|\$[A-Za-z0-9_]+|\^[A-Za-z0-9]{2}|<[^>]+>|\\(?:[A-Za-z0-9]+|.)|[\x00-\x1f]",
        s,
    )


def translation_tokens(row):
    """Normalize explicitly reviewed literal spans, never arbitrary @ tokens.

    Source metadata remains original; verify_sources binds annotations to the
    complete source hash and verifies delimiter count against the real input.
    """
    text = row.get("translation", "")
    mappings = row.get("literal_token_translations", [])
    seen = set()
    for mapping in mappings:
        source, target = mapping["source"], mapping["translation"]
        if source in seen or source not in row["tokens"]:
            raise ValueError("Invalid or duplicate literal token annotation")
        seen.add(source)
        for span in (source, target):
            if (
                not span.startswith("@")
                or not span.endswith("@")
                or span.count("@") != 2
                or len(span) <= 2
            ):
                raise ValueError("Literal spans must retain paired @ delimiters")
            if tokens(span[1:-1]):
                raise ValueError("Literal span contains a protected control")
        if text.count(target) != row["tokens"].count(source):
            raise ValueError("Literal span missing or duplicated")
        text = text.replace(target, source)
    if mappings and row.get("markup_delimiter_count") != row.get(
        "translation", ""
    ).count("@"):
        raise ValueError("Literal markup delimiter count changed")
    return tokens(text)


def entries(path):
    b = path.read_bytes()
    t, e = decode(b)
    sec = ""
    out = []
    counts = collections.Counter()
    for n, line in enumerate(t.splitlines(), 1):
        m = re.match(r"^\s*\[([^]]+)\]", line)
        if m:
            sec = m[1]
            continue
        m = re.match(r"^(\s*[^;#=]+?)=(.*)$", line)
        if not m:
            continue
        key = m[1].strip()
        raw = m[2]
        v = raw.strip()
        quoted = len(v) >= 2 and v[0] == v[-1] == '"'
        v = v[1:-1] if quoted else v
        counts[(sec, key)] += 1
        out.append(
            dict(
                file=path.name,
                section=sec,
                key=key,
                occurrence=counts[(sec, key)],
                line=n,
                source=v,
                translation="",
                tokens=tokens(v),
                quoted=quoted,
                encoding=e,
                empty=v == "",
                kind=(
                    "structured-metadata"
                    if sec.lower() == "public"
                    and key.lower() in ["object", "preferences"]
                    else "string-candidate"
                ),
            )
        )
    return out
