"""Versioned COPY/LITERAL delta. All bytes are hash-gated before installation.

This format is for locally built artifacts; no full game resource is bundled.
It is not an authenticated format: use only trusted build artifacts.
"""

import base64
import hashlib
import zlib


def sha(data):
    return hashlib.sha256(data).hexdigest()


def create(original, modified, block=512):
    index = {}
    for i in range(0, len(original) - block + 1, block):
        index.setdefault(original[i : i + block], i)
    ops = []
    literal = bytearray()

    def flush():
        if literal:
            ops.append(
                {
                    "literal": base64.b64encode(
                        zlib.compress(bytes(literal), 9)
                    ).decode("ascii"),
                    "size": len(literal),
                }
            )
            literal.clear()

    i = 0
    while i < len(modified):
        match = (
            index.get(modified[i : i + block]) if i + block <= len(modified) else None
        )
        if match is not None:
            flush()
            count = block
            while (
                match + count + block <= len(original)
                and i + count + block <= len(modified)
                and original[match + count : match + count + block]
                == modified[i + count : i + count + block]
            ):
                count += block
            ops.append({"copy": match, "size": count})
            i += count
        else:
            literal.append(modified[i])
            i += 1
    flush()
    return {
        "format": "copy-literal-v1",
        "original_sha256": sha(original),
        "original_size": len(original),
        "modified_sha256": sha(modified),
        "modified_size": len(modified),
        "operations": ops,
    }


def apply(original, delta):
    if delta["format"] != "copy-literal-v1":
        raise ValueError("Unknown delta format")
    if (
        len(original) != delta["original_size"]
        or sha(original) != delta["original_sha256"]
    ):
        raise ValueError("Original fingerprint differs")
    out = bytearray()
    for op in delta["operations"]:
        n = op["size"]
        if n < 0 or len(out) + n > delta["modified_size"]:
            raise ValueError("Invalid delta size")
        if "copy" in op:
            start = op["copy"]
            if start < 0 or start + n > len(original):
                raise ValueError("Invalid COPY range")
            data = original[start : start + n]
        else:
            decoder = zlib.decompressobj()
            data = decoder.decompress(
                base64.b64decode(op["literal"], validate=True), n + 1
            )
            if not decoder.eof or decoder.unused_data or decoder.unconsumed_tail:
                raise ValueError("Invalid LITERAL stream")
        if len(data) != n:
            raise ValueError("Invalid LITERAL size")
        out.extend(data)
    if len(out) != delta["modified_size"] or sha(out) != delta["modified_sha256"]:
        raise ValueError("Modified fingerprint differs")
    return bytes(out)
