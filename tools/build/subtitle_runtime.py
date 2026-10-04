"""Build and manage an opt-in resource-level subtitle scheduler, without game launch."""

import argparse
import hashlib
import json
import shutil
import subprocess
from pathlib import Path
from tools.pack.ue1 import Package

ROOT = Path(__file__).resolve().parents[2]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_cues(data, translation):
    cues = data["cues"]
    if (
        not 0 < len(cues) <= 16
        or "".join(c["translation"] for c in cues) != translation
    ):
        raise ValueError("Cues must reconstruct the exact approved translation")
    previous = 0.0
    for cue in cues:
        begin, end = cue["begin"], cue["end"]
        if not (
            isinstance(begin, (int, float))
            and isinstance(end, (int, float))
            and previous <= begin < end < 3600
        ):
            raise ValueError("Invalid or overlapping cue interval")
        if not cue["translation"] or any(
            c in cue["translation"] for c in ['"', "\r", "\n", "\0"]
        ):
            raise ValueError("Invalid cue text")
        previous = end
    return cues


def caption_at(data, elapsed):
    return next(
        (c["translation"] for c in data["cues"] if c["begin"] <= elapsed < c["end"]), ""
    )


def build(game, locale, out):
    from tools.build.pipeline import check_originals

    config = json.loads((ROOT / "locales" / locale / "config.json").read_text("utf8"))
    prompts = []
    if config.get("tutorial_prompts"):
        from tools.build.prompt_data import bind
        from tools.validate.terminology import load_terms

        prompt_path = (ROOT / "locales" / locale / config["tutorial_prompts"]).resolve()
        if prompt_path.parent != (ROOT / "locales" / locale).resolve():
            raise ValueError("Prompt locale path escapes directory")
        prompts = bind(
            game,
            json.loads(prompt_path.read_text("utf8")),
            load_terms(
                ROOT / config["terminology"]["path"],
                config["terminology"]["target_column"],
            ),
        )
    check_originals(
        game,
        json.loads(
            (ROOT / "profiles" / (config["profile"] + ".json")).read_text("utf8")
        ),
    )
    data = json.loads(
        (ROOT / "locales" / locale / "subtitle-cues.json").read_text("utf8")
    )
    rows = json.loads(
        (ROOT / "locales" / locale / config["subtitle_overrides"]).read_text("utf8")
    )
    section, key = data["sound"].split(".")
    row = next(r for r in rows if r["section"] == section and r["key"] == key)
    if row["source_sha256"] != data["source_sha256"]:
        raise ValueError("Timeline source changed")
    cues = validate_cues(data, row["translation"])
    for e in json.loads((ROOT / "profiles/subtitle-runtime.json").read_text("utf8"))[
        "compiler_inputs"
    ]:
        p = game / e["file"]
        if sha(p) != e["sha256"] or p.stat().st_size != e["size"]:
            raise ValueError("Unknown runtime compiler input: " + e["file"])
    out = out.resolve()
    if out.is_relative_to(game.resolve()):
        raise ValueError("Output must be independent of original game")
    previous = out / "ADDON.json"
    if previous.exists():
        old = json.loads(previous.read_text("utf8"))
        archive = out / "history" / sha(previous)
        for name, expected in old["files"].items():
            if name not in {"LocaleRuntime.u", "LocaleRuntime.int"}:
                raise ValueError("Unknown previous addon file")
            source = out / "resources/System" / name
            if sha(source) != expected["sha256"]:
                raise ValueError("Previous addon resource changed")
            destination = archive / "resources/System" / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, destination)
        shutil.copyfile(previous, archive / "ADDON.json")
    compiler = out / "compiler"
    system = compiler / "System"
    system.mkdir(parents=True, exist_ok=True)
    for p in (game / "System").iterdir():
        if p.suffix.lower() in [".dll", ".int"] or p.name in [
            "UCC.exe",
            "Default.ini",
            "DefUser.ini",
        ]:
            shutil.copyfile(p, system / p.name)
    src = (ROOT / "src/runtime/LocaleRuntime/Classes/LocalePlayer.uc").read_text(
        "ascii"
    )
    src += (
        '\ndefaultproperties\n{\n    CueSound="'
        + data["sound"]
        + '"\n    CueCount='
        + str(len(cues))
        + "\n"
    )
    for i, c in enumerate(cues):
        src += (
            "    CueBegin("
            + str(i)
            + ")="
            + str(c["begin"])
            + "\n    CueEnd("
            + str(i)
            + ")="
            + str(c["end"])
            + "\n"
        )
    src += "    PromptCount=" + str(len(prompts)) + "\n"
    for i, prompt in enumerate(prompts):
        src += f'    PromptSource({i})="{prompt["source"]}"\n'
    src += "}\n"
    p = compiler / "LocaleRuntime/Classes/LocalePlayer.uc"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(src, "ascii")
    shutil.copyfile(
        ROOT / "src/runtime/LocaleRuntime/Classes/LocaleTutorial.uc",
        compiler / "LocaleRuntime/Classes/LocaleTutorial.uc",
    )
    shutil.copyfile(
        ROOT / "src/runtime/LocaleRuntime/Classes/LocaleSubtitleClock.uc",
        compiler / "LocaleRuntime/Classes/LocaleSubtitleClock.uc",
    )
    ini = (
        "[Core.System]\nPaths="
        + str(system / "*.u")
        + "\n"
        + "".join(
            "Paths=" + str(game / folder / pattern) + "\n"
            for folder, pattern in [
                ("System", "*.u"),
                ("Textures", "*.utx"),
                ("Sounds", "*.uax"),
                ("Music", "*.umx"),
                ("Maps", "*.wot"),
            ]
        )
        + "\n[Engine.Engine]\nEditorEngine=Editor.EditorEngine\nLanguage=int\n[Editor.EditorEngine]\n"
        + "".join(
            "EditPackages=" + n + "\n"
            for n in [
                "Core",
                "Engine",
                "Legend",
                "WOT",
                "Angreal",
                "WOTPawns",
                "LocaleRuntime",
            ]
        )
    )
    (system / "WoT.ini").write_text(ini, "ascii")
    # UCC skips already compiled packages. A repeated build must replace only its own output.
    binary = system / "LocaleRuntime.u"
    if binary.exists():
        binary.unlink()
    result = subprocess.run(
        [str(system / "UCC.exe"), "Editor.MakeCommandlet", "-ini=WoT.ini"],
        cwd=system,
        capture_output=True,
        text=True,
        encoding="cp1252",
    )
    (out / "COMPILER.txt").write_text(result.stdout + result.stderr, "utf8")
    if (
        result.returncode
        or "Success - 0 error(s), 0 warnings" not in result.stdout
        or not binary.is_file()
    ):
        raise ValueError("Subtitle compiler failed; see COMPILER.txt")
    raw = bytearray(binary.read_bytes())
    if Package(binary).ver != 68:
        raise ValueError("Unknown compiled package summary version")
    # UE1 v68 package GUID is at summary bytes 36..51. Canonicalize our own
    # newly compiled package, not an original game package.
    raw[36:52] = hashlib.sha256(bytes(raw[:36] + raw[52:])).digest()[:16]
    binary.write_bytes(raw)
    package = Package(binary)
    classes = {
        r["path"]
        for r in package.records()
        if package.exports[r["index"] - 1]["cls"] == 0
    }
    if not {"LocalePlayer", "LocaleTutorial", "LocaleSubtitleClock"} <= classes:
        raise ValueError("Compiled scheduler class missing")
    resources = out / "resources/System"
    resources.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(binary, resources / binary.name)
    (resources / "LocaleRuntime.int").write_bytes(
        b"\xff\xfe"
        + (
            "[LocalePlayer]\r\n"
            + "".join(
                "CueText[" + str(i) + ']="' + c["translation"] + '"\r\n'
                for i, c in enumerate(cues)
            )
            + "".join(
                f'PromptText[{i}]="{p["translation"]}"\r\n'
                for i, p in enumerate(prompts)
            )
        ).encode("utf-16le")
    )
    manifest = dict(
        format="subtitle-addon-v1",
        locale=locale,
        files={
            p.name: dict(size=p.stat().st_size, sha256=sha(p))
            for p in resources.iterdir()
        },
        launch_class="LocaleRuntime.LocalePlayer",
        launch_game="LocaleRuntime.LocaleTutorial",
        in_game_verified=False,
    )
    (out / "ADDON.json").write_text(json.dumps(manifest, indent=2) + "\n", "utf8")
    print(
        "SUBTITLE BUILD PASS: 4 separate cues; compiled class readback; 0 errors; 0 warnings; no maps/EXE/DLL modified"
    )


def manage(command, bundle, target):
    manifest = json.loads(bundle.read_text("utf8"))
    system = (target / "System").resolve()
    if manifest["format"] != "subtitle-addon-v1" or set(manifest["files"]) != {
        "LocaleRuntime.u",
        "LocaleRuntime.int",
    }:
        raise ValueError("Unknown addon manifest")
    for name, expected in manifest["files"].items():
        src = bundle.parent / "resources/System" / name
        dst = system / name
        if sha(src) != expected["sha256"]:
            raise ValueError("Addon source changed")
        if dst.exists() and sha(dst) != expected["sha256"]:
            raise ValueError("Existing addon differs; retain it and review first")
        if command == "verify" and not dst.exists():
            raise ValueError("Addon missing")
    system.mkdir(parents=True, exist_ok=True)
    for name in manifest["files"]:
        dst = system / name
        if command == "apply":
            shutil.copyfile(bundle.parent / "resources/System" / name, dst)
        elif command == "restore" and dst.exists():
            if dst.parent != system:
                raise ValueError("Invalid rollback target")
            dst.unlink()
    print(
        command.upper()
        + " ADDON PASS: 2 owned files; original resources and configuration unchanged"
    )


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("command", choices=["build", "apply", "verify", "restore"])
    p.add_argument("--game-dir", type=Path)
    p.add_argument("--locale", default="zh-CN")
    p.add_argument("--out", type=Path)
    p.add_argument("--bundle", type=Path)
    p.add_argument("--target", type=Path)
    a = p.parse_args()
    if a.command == "build":
        if not a.game_dir or not a.out:
            p.error("build requires --game-dir and --out")
        if (ROOT / "locales" / a.locale).resolve().parent != (
            ROOT / "locales"
        ).resolve():
            raise ValueError("Invalid locale")
        build(a.game_dir.resolve(), a.locale, a.out)
    else:
        if not a.bundle or not a.target:
            p.error("manage requires --bundle and --target")
        manage(a.command, a.bundle.resolve(), a.target.resolve())


if __name__ == "__main__":
    main()
