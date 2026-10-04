"""Read-only timed legacy QuickTime text export. Never transcribes or re-encodes."""

import argparse
import hashlib
import json
import subprocess
from pathlib import Path


def decode_sample(data):
    if len(data) < 2:
        raise ValueError("Truncated QuickTime text sample")
    size = int.from_bytes(data[:2], "big")
    if size > len(data) - 2:
        raise ValueError("QuickTime text length exceeds sample")
    text = data[2 : 2 + size]
    if text.startswith(b"\xfe\xff"):
        return text[2:].decode("utf-16be"), "utf-16be-bom"
    if text.startswith(b"\xff\xfe"):
        return text[2:].decode("utf-16le"), "utf-16le-bom"
    return text.decode("mac_roman"), "mac-roman-assumed"


def extract(movie, ffprobe, out):
    result = subprocess.run(
        [
            str(ffprobe),
            "-v",
            "error",
            "-show_streams",
            "-show_format",
            "-of",
            "json",
            str(movie),
        ],
        capture_output=True,
    )
    if result.returncode:
        raise ValueError(result.stderr.decode("utf8", errors="replace"))
    metadata = json.loads(result.stdout)
    report = dict(
        movie=movie.name,
        size=movie.stat().st_size,
        sha256=hashlib.sha256(movie.read_bytes()).hexdigest(),
        duration=metadata.get("format", {}).get("duration"),
        streams=metadata["streams"],
        tracks=[],
    )
    packets = subprocess.run(
        [
            str(ffprobe),
            "-v",
            "error",
            "-select_streams",
            "s",
            "-show_packets",
            "-show_entries",
            "packet=stream_index,pts_time,duration_time,pos,size",
            "-of",
            "json",
            str(movie),
        ],
        capture_output=True,
    )
    if packets.returncode:
        raise ValueError("Subtitle packet probe failed")
    groups = {}
    with movie.open("rb") as source:
        for packet in json.loads(packets.stdout).get("packets", []):
            pos, size = int(packet["pos"]), int(packet["size"])
            if pos < 0 or size < 2 or pos + size > movie.stat().st_size:
                raise ValueError("Text packet outside movie")
            source.seek(pos)
            text, encoding = decode_sample(source.read(size))
            groups.setdefault(packet["stream_index"], []).append(
                dict(
                    begin=packet.get("pts_time"),
                    duration=packet.get("duration_time"),
                    offset=pos,
                    size=size,
                    text=text,
                    encoding=encoding,
                )
            )
    out.mkdir(parents=True, exist_ok=True)
    for index, rows in groups.items():
        destination = out / f"{movie.stem}.stream{index}.json"
        destination.write_text(json.dumps(rows, ensure_ascii=False, indent=2), "utf8")
        stream = next(s for s in metadata["streams"] if s["index"] == index)
        report["tracks"].append(
            dict(
                index=index,
                language=stream.get("tags", {}).get("language"),
                samples=len(rows),
                nonempty=sum(bool(r["text"].strip()) for r in rows),
                data=destination.name,
            )
        )
    if hashlib.sha256(movie.read_bytes()).hexdigest() != report["sha256"]:
        raise ValueError("Movie changed during extraction")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--movies", type=Path, required=True)
    parser.add_argument("--ffprobe", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.out.resolve().is_relative_to(args.movies.resolve()):
        raise ValueError("Output must be outside original movies")
    reports = [
        extract(p, args.ffprobe, args.out) for p in sorted(args.movies.glob("*.mov"))
    ]
    (args.out / "MANIFEST.json").write_text(
        json.dumps(reports, ensure_ascii=False, indent=2), "utf8"
    )
    print(
        f"MOVIE TEXT PASS: {len(reports)} movies; "
        f'{sum(len(r["tracks"]) for r in reports)} tracks; originals unchanged'
    )


if __name__ == "__main__":
    main()
