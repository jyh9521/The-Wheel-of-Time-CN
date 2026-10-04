"""Build an independent 1080p native QuickTime preview, never install or launch it."""
import argparse
import json
import os
import re
import subprocess
from pathlib import Path

from tools.pack.movie_text_probe import build, sha

ROOT = Path(__file__).resolve().parents[2]


def runtime_directory():
    import winreg
    with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                        r"SOFTWARE\Apple Computer, Inc.\QuickTime", 0,
                        winreg.KEY_READ | winreg.KEY_WOW64_32KEY) as key:
        return Path(winreg.QueryValueEx(key, "QTSysDir")[0])


def write_owned(path, data):
    if path.exists() and path.read_bytes() != data:
        if path.suffix == ".json" and json.loads(path.read_bytes()) == json.loads(data):
            return  # Preserve an identical manifest with Windows line endings.
        raise ValueError(f"Existing output differs; choose a fresh --out: {path}")
    path.write_bytes(data)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--game-dir", type=Path, required=True)
    parser.add_argument("--qt-dir", type=Path)
    parser.add_argument("--locale", default="zh-CN")
    parser.add_argument("--out", type=Path, default=ROOT / "build/fmv-preview")
    args = parser.parse_args()
    if not re.fullmatch(r"[A-Za-z0-9-]+", args.locale):
        raise ValueError("Invalid locale directory name")
    game, out = args.game_dir.resolve(), args.out.resolve()
    if out.is_relative_to(game):
        raise ValueError("Preview output must be outside original game directory")
    qt = (args.qt_dir or runtime_directory()).resolve()
    if not (qt / "QTMLClient.dll").is_file():
        raise ValueError("Installed QuickTime runtime missing")
    config = json.loads((ROOT / "locales" / args.locale / "fmv_probe.json").read_text("utf8"))
    movie_name = config.get("movie", "Intro.mov")
    if Path(movie_name).name != movie_name or not movie_name.lower().endswith(".mov"):
        raise ValueError("Movie must be a basename, not an arbitrary source path")
    source = game / "Movies" / movie_name
    original = source.read_bytes()
    modified, diff = build(original, config)
    compiler = Path(os.environ["WINDIR"]) / "Microsoft.NET/Framework/v4.0.30319/csc.exe"
    if not compiler.is_file():
        raise ValueError("Windows .NET Framework 4 csc.exe missing")
    out.mkdir(parents=True, exist_ok=True)
    write_owned(out / "MODIFIED_FILE.mov", modified)
    write_owned(out / "DIFF_FILE.json", json.dumps(diff, indent=2).encode("utf8"))
    exe = out / "quicktime_player.exe"
    subprocess.run([str(compiler), "/nologo", "/platform:x86", "/r:System.Drawing.dll",
                    "/r:System.Windows.Forms.dll", "/out:" + str(exe),
                    str(ROOT / "tools/validate/quicktime_player.cs")], check=True)
    manifest = dict(locale=args.locale, source=str(source), source_sha256=sha(original),
                    movie="MODIFIED_FILE.mov", movie_sha256=sha(modified),
                    player="quicktime_player.exe", player_sha256=sha(exe.read_bytes()),
                    qt_dir=str(qt), canvas=[1920, 1080], sample_seconds=[1, 7],
                    experiment_only=True, game_installed=False)
    (out / "PREVIEW.json").write_text(json.dumps(manifest, indent=2), "utf8")
    launcher = '''$ErrorActionPreference = 'Stop'
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$config = Get-Content -LiteralPath (Join-Path $here 'PREVIEW.json') -Raw | ConvertFrom-Json
$movie = Join-Path $here $config.movie
$player = Join-Path $here $config.player
if ((Get-FileHash -LiteralPath $movie -Algorithm SHA256).Hash.ToLowerInvariant() -ne $config.movie_sha256) { throw 'Preview movie SHA-256 mismatch' }
if ((Get-FileHash -LiteralPath $player -Algorithm SHA256).Hash.ToLowerInvariant() -ne $config.player_sha256) { throw 'Preview player SHA-256 mismatch' }
& $player play $config.qt_dir $movie on
exit $LASTEXITCODE
'''
    (out / "PLAY_FMV.ps1").write_text(launcher, "utf8")
    rollback = '''#!/usr/bin/env bash
set -euo pipefail
dir="$(cd "$(dirname "$0")" && pwd)"
cd "$(cygpath -u "{root}")"
python -m tools.pack.movie_text_probe restore --input "$dir/MODIFIED_FILE.mov" --diff "$dir/DIFF_FILE.json" --output "${{1:?Supply a NEW rollback copy path}}"
'''.format(root=str(ROOT).replace("\\", "/"))
    (out / "ROLLBACK.sh").write_text(rollback, "utf8")
    if sha(source.read_bytes()) != sha(original):
        raise ValueError("Original movie changed during build")
    print("FMV PREVIEW BUILD PASS: 1920x1080; native text; original unchanged; no game install")
    print("LAUNCHER: " + str(out / "PLAY_FMV.ps1"))


if __name__ == "__main__":
    main()
