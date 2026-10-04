"""Isolated legacy MOV text sample experiment; never re-encode or install movies."""
import argparse
import hashlib
import json
import struct
from pathlib import Path

from tools.extract.movie_text import decode_sample


def sha(data):
    return hashlib.sha256(data).hexdigest()


def atoms(data, start=0, end=None):
    end = len(data) if end is None else end
    while start < end:
        if end - start < 8:
            raise ValueError("Truncated atom header")
        size, kind = struct.unpack_from(">I4s", data, start)
        if size == 1:
            raise ValueError("Extended-size atoms not supported by this probe")
        size = end - start if size == 0 else size
        if size < 8 or start + size > end:
            raise ValueError("Atom outside container")
        yield kind, start, size
        start += size


def child(data, parent, kind):
    matches = [a for a in atoms(data, parent[1] + 8, parent[1] + parent[2]) if a[0] == kind]
    if len(matches) != 1:
        raise ValueError(f"Expected one {kind!r} atom")
    return matches[0]


def tables(data, track_id):
    root = (b"root", -8, len(data) + 8)
    moov = child(data, root, b"moov")
    for track in atoms(data, moov[1] + 8, moov[1] + moov[2]):
        if track[0] != b"trak":
            continue
        tkhd = child(data, track, b"tkhd")
        if data[tkhd[1] + 8] != 0:
            raise ValueError("Only version-zero track headers supported")
        if struct.unpack_from(">I", data, tkhd[1] + 20)[0] != track_id:
            continue
        mdia = child(data, track, b"mdia")
        handler = child(data, mdia, b"hdlr")
        if data[handler[1] + 16:handler[1] + 20] != b"text":
            raise ValueError("Target is not a legacy text track")
        stbl = child(data, child(data, mdia, b"minf"), b"stbl")
        result = {k.decode(): child(data, stbl, k) for k in (b"stsd", b"stsz", b"stco", b"stsc")}
        count = struct.unpack_from(">I", data, result["stsz"][1] + 16)[0]
        sc = result["stsc"]
        if data[sc[1] + 12:sc[1] + sc[2]] != struct.pack(">IIII", 1, 1, 1, 1):
            raise ValueError("Probe requires one sample per chunk, one description")
        sz, co = result["stsz"], result["stco"]
        if struct.unpack_from(">I", data, sz[1] + 12)[0] != 0 or sz[2] != 20 + count * 4:
            raise ValueError("Expected explicit sample sizes")
        if co[2] != 16 + count * 4 or struct.unpack_from(">I", data, co[1] + 12)[0] != count:
            raise ValueError("Sample and chunk counts differ")
        result.update(track=track, tkhd=tkhd, count=count)
        return result
    raise ValueError("Track ID not found")


def sample(data, track_id, index):
    t = tables(data, track_id)
    if not 0 <= index < t["count"]:
        raise ValueError("Sample index out of range")
    size = struct.unpack_from(">I", data, t["stsz"][1] + 20 + 4 * index)[0]
    offset = struct.unpack_from(">I", data, t["stco"][1] + 16 + 4 * index)[0]
    containers = [(a[1] + 8, a[1] + a[2]) for a in atoms(data) if a[0] == b"mdat"]
    if not any(begin <= offset and offset + size <= end for begin, end in containers):
        raise ValueError("Sample outside media data")
    return data[offset:offset + size]


def build(data, config):
    if sha(data) != config["source_sha256"]:
        raise ValueError("Source SHA-256 mismatch")
    track_id, index = config["track_id"], config["sample_index"]
    original = sample(data, track_id, index)
    if sha(original) != config["sample_sha256"]:
        raise ValueError("Source sample SHA-256 mismatch")
    text = b"\xfe\xff" + config["text"].encode("utf-16be")
    if len(text) > 65535:
        raise ValueError("Text exceeds 16-bit byte length")
    # Old styl/ftab/orig modifiers contain obsolete character offsets/text.
    # QA1400: BOM alone is insufficient for the legacy text media handler.
    # encd stores kTextEncodingUnicodeDefault (0x100), not a character count.
    replacement = struct.pack(">H", len(text)) + text + struct.pack(">I4sI", 12, b"encd", 0x100)
    t = tables(data, track_id)
    result = bytearray(data)
    edits = []

    def edit(offset, new):
        old = bytes(result[offset:offset + len(new)])
        edits.append(dict(offset=offset, before=old.hex(), after=new.hex()))
        result[offset:offset + len(new)] = new

    edit(t["stsz"][1] + 20 + index * 4, struct.pack(">I", len(replacement)))
    edit(t["stco"][1] + 16 + index * 4, struct.pack(">I", len(data) + 8))
    flags = int.from_bytes(data[t["tkhd"][1] + 9:t["tkhd"][1] + 12], "big")
    edit(t["tkhd"][1] + 9, (flags | 1).to_bytes(3, "big"))
    if "media_language" in config:
        language = config["media_language"]
        if not isinstance(language, int) or not 0 <= language <= 32767:
            raise ValueError("Invalid legacy media language code")
        mdhd = child(data, child(data, t["track"], b"mdia"), b"mdhd")
        if mdhd[2] != 32 or data[mdhd[1] + 8] != 0:
            raise ValueError("Expected version-zero media header")
        edit(mdhd[1] + 28, struct.pack(">H", language))
    if config.get("font"):
        before = config["source_font"].encode("ascii")
        after = config["font"].encode("ascii")
        if len(before) != len(after) or not before:
            raise ValueError("Probe requires equal-length ASCII font names")
        desc = t["stsd"]
        body = data[desc[1]:desc[1] + desc[2]]
        needle = bytes([len(before)]) + before
        if body.count(needle) != 1:
            raise ValueError("Expected exactly one Pascal source font name")
        edit(desc[1] + body.index(needle) + 1, after)
    result.extend(struct.pack(">I4s", len(replacement) + 8, b"mdat") + replacement)
    # Appending after a zero-size mdat would consume the new header as payload.
    if any(struct.unpack_from(">I", data, a[1])[0] == 0 for a in atoms(data)):
        raise ValueError("Zero-size top-level atoms cannot be appended")
    result = bytes(result)
    if decode_sample(sample(result, track_id, index))[0] != config["text"]:
        raise ValueError("Text read-back mismatch")
    manifest = dict(source_sha256=sha(data), output_sha256=sha(result),
                    source_size=len(data), output_size=len(result), edits=edits,
                    track_id=track_id, sample_index=index,
                    removed_sample_modifiers=True,
                    text_encoding_atom="encd:0x100",
                    original_mdat_sha256=[sha(data[a[1] + 8:a[1] + a[2]]) for a in atoms(data) if a[0] == b"mdat"])
    for a in atoms(data):
        if a[0] == b"mdat" and result[a[1]:a[1] + a[2]] != data[a[1]:a[1] + a[2]]:
            raise ValueError("Original media payload changed")
    return result, manifest


def restore(data, manifest):
    if len(data) != manifest["output_size"] or sha(data) != manifest["output_sha256"]:
        raise ValueError("Modified movie identity mismatch")
    result = bytearray(data[:manifest["source_size"]])
    for edit in reversed(manifest["edits"]):
        offset, old, new = edit["offset"], bytes.fromhex(edit["before"]), bytes.fromhex(edit["after"])
        if result[offset:offset + len(new)] != new:
            raise ValueError("Rollback field mismatch")
        result[offset:offset + len(new)] = old
    if sha(result) != manifest["source_sha256"]:
        raise ValueError("Rollback SHA-256 mismatch")
    return bytes(result)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("build", "probe", "restore"))
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--config", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--diff", type=Path)
    parser.add_argument("--track", type=int, default=3)
    parser.add_argument("--sample", type=int, default=1)
    args = parser.parse_args()
    data = args.input.read_bytes()
    if args.mode == "probe":
        text, encoding = decode_sample(sample(data, args.track, args.sample))
        print(json.dumps(dict(text=text, encoding=encoding, sha256=sha(data)), ensure_ascii=True))
        return
    if not args.output or not args.diff or (args.mode == "build" and not args.config):
        parser.error("build/restore require output/diff; build also requires config")
    if args.output.resolve() == args.input.resolve() or args.output.exists():
        raise ValueError("Output must be a new copy")
    if args.mode == "build":
        if args.diff.exists() or args.diff.resolve() in (args.input.resolve(), args.output.resolve(), args.config.resolve()):
            raise ValueError("Diff must be a separate new file")
        result, manifest = build(data, json.loads(args.config.read_text("utf8")))
        args.diff.parent.mkdir(parents=True, exist_ok=True)
        args.diff.write_text(json.dumps(manifest, indent=2), "utf8")
    else:
        result = restore(data, json.loads(args.diff.read_text("utf8")))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(result)
    print(f"{args.mode.upper()} PASS: {len(result)} bytes; sha256={sha(result)}")


if __name__ == "__main__":
    main()
