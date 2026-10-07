"""Build a standalone, hash-gated Windows player test package (no Python at install)."""
import argparse
import base64
import hashlib
import json
from pathlib import Path
import sys
import zipfile
import zlib

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from src.patch.delta import apply, create, sha


def package(game, resources, runtime, output, locale="zh-CN"):
    bundle = json.loads((resources / "PATCH.json").read_text(encoding="utf-8"))
    if bundle["locale"] != locale:
        raise ValueError("Resource locale differs")
    entries, members = [], {}

    def add(path, original, modified, delta=None, owned=False):
        if original == modified and not owned:
            return
        delta = delta or create(original, modified)
        if apply(original, delta) != modified:
            raise ValueError("Delta verification failed: " + path)
        operations = []
        for op in delta["operations"]:
            if "copy" in op:
                operations.append(dict(op))
            else:
                data = zlib.decompress(base64.b64decode(op["literal"], validate=True))
                if len(data) != op["size"]:
                    raise ValueError("Literal length differs")
                name = "payload/" + sha(data) + ".bin"
                members["LocalizationTest/" + name] = data
                operations.append({"payload": name, "sha256": sha(data), "size": len(data)})
        entries.append({"path": path, "owned": owned,
                        **{k: v for k, v in delta.items() if k not in ("operations", "format")},
                        "operations": operations})

    for path, delta in sorted(bundle["files"].items()):
        owned = path in bundle.get("owned_additions", [])
        original = b"" if owned else (game / path).read_bytes()
        modified = apply(original, delta)
        if (runtime / path).read_bytes() != modified:
            raise ValueError("Accepted runtime differs from resource build: " + path)
        add(path, original, modified, delta, owned)

    for movie in sorted((runtime / "Movies").glob("*.mov")):
        original, modified = (game / "Movies" / movie.name).read_bytes(), movie.read_bytes()
        if original == modified:
            continue
        # MOV rebuilds retain media and append translated text samples. Convert the
        # sparse differences in the original-length prefix without indexing media.
        ops, at = [], 0
        while at < len(original):
            block_end = min(at + 65536, len(original))
            if original[at:block_end] == modified[at:block_end]:
                if ops and "copy" in ops[-1] and ops[-1]["copy"] + ops[-1]["size"] == at:
                    ops[-1]["size"] += block_end-at
                else:
                    ops.append({"copy": at, "size": block_end-at})
                at = block_end
                continue
            start = at
            same = original[at] == modified[at]
            while at < block_end and (original[at] == modified[at]) == same:
                at += 1
            if same:
                ops.append({"copy": start, "size": at-start})
            else:
                ops.append({"literal": base64.b64encode(zlib.compress(modified[start:at])).decode(), "size": at-start})
        if len(modified) > len(original):
            tail = modified[len(original):]
            ops.append({"literal": base64.b64encode(zlib.compress(tail)).decode(), "size": len(tail)})
        delta = {"format": "copy-literal-v1", "original_sha256": sha(original), "original_size": len(original),
                 "modified_sha256": sha(modified), "modified_size": len(modified), "operations": ops}
        add("Movies/" + movie.name, original, modified, delta)

    add("System/WinDrv.dll", (game / "System/WinDrv.dll").read_bytes(), (runtime / "System/WinDrv.dll").read_bytes())
    for name in ("WotFmv.ttf", "OFL.txt"):
        add("Fonts/" + name, b"", (runtime / "Fonts" / name).read_bytes(), owned=True)
    manifest = {"format": "player-test-v1", "locale": locale,
                "version": "GOG v68", "files": entries,
                "launch": {"path": "System/WoT.exe", "sha256": sha((game / "System/WoT.exe").read_bytes())},
                "config": [{"path": "System/User.ini", "section": "WOT.WOTPlayer", "key": "bSubtitles", "value": "True"},
                           {"path": "System/WoT.ini", "section": "Engine.Engine", "key": "Language", "value": "int"}]}
    slot_path=ROOT/'locales'/locale/'save-slots.json'
    if slot_path.exists():
        slots=json.loads(slot_path.read_text('utf8'))
        manifest['config'] += [dict(path=slots['path'],section=slots['section'],key=key,value=slots['translation'],match_values=slots['match_values']) for key in slots['keys']]
    members["LocalizationTest/MANIFEST.json"] = json.dumps(manifest, ensure_ascii=False, indent=2).encode("utf-8")
    members["LocalizationTest/Manage-Patch.ps1"] = (ROOT / "assets/templates/player-test.ps1").read_bytes()
    for name, action in (("Install-Localization", "apply"), ("Verify-Localization", "verify"),
                         ("Uninstall-Localization", "restore"), ("Launch-Game", "launch")):
        members[name + ".cmd"] = (f'@echo off\r\npowershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0LocalizationTest\\Manage-Patch.ps1" -Action {action} -GameDir "%~dp0."\r\nset "RESULT=%ERRORLEVEL%"\r\nif not "%RESULT%"=="0" pause\r\nexit /b %RESULT%\r\n').encode("ascii")
    members["TESTING.md"] = (ROOT / "docs/PLAYER_TEST_PACKAGE.md").read_bytes()
    for name in ("LICENSE", "LICENSE-translations.md", "LICENSING.md"):
        members["LocalizationTest/licenses/" + name] = (ROOT / name).read_bytes()
    members["LocalizationTest/CONTENTS.json"] = json.dumps({k: sha(v) for k, v in sorted(members.items())}, indent=2).encode()
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name, data in sorted(members.items()):
            info = zipfile.ZipInfo(name, date_time=(2020, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, data)
    with zipfile.ZipFile(output) as archive:
        if archive.testzip() is not None:
            raise ValueError("ZIP integrity failed")
        for name, data in members.items():
            if archive.read(name) != data:
                raise ValueError("ZIP readback differs")
    output.with_suffix(".zip.sha256").write_text(sha(output.read_bytes()) + "  " + output.name + "\n", encoding="ascii")
    print(f"PACKAGE PASS: resources={len(entries)} movies={sum(e['path'].startswith('Movies/') for e in entries)} bytes={output.stat().st_size}")
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--game-dir", type=Path, required=True)
    parser.add_argument("--resource-build", type=Path, required=True)
    parser.add_argument("--runtime-dir", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--locale", default="zh-CN")
    args = parser.parse_args()
    package(args.game_dir, args.resource_build, args.runtime_dir, args.out, args.locale)
