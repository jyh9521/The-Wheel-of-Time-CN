"""Reproducible resource-only localization entry point."""

import argparse
import importlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def main():
    if not __debug__:
        raise ValueError("Do not use python -O; package integrity assertions must run")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "command",
        nargs="?",
        default="build",
        choices=["build", "validate", "extract", "test"],
    )
    parser.add_argument("--locale", default="zh-CN")
    parser.add_argument("--game-dir", type=Path)
    parser.add_argument("--font", type=Path)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()
    if args.command == "test":
        import unittest

        result = unittest.TextTestRunner(verbosity=2).run(
            unittest.defaultTestLoader.discover(str(ROOT / "tests"))
        )
        return 0 if result.wasSuccessful() else 1
    locale = (ROOT / "locales" / args.locale).resolve()
    if locale.parent != (ROOT / "locales").resolve():
        raise ValueError("Invalid locale identifier")
    config = json.loads((locale / "config.json").read_text("utf8"))
    if config["locale"] != args.locale:
        raise ValueError("Locale identifier mismatch")
    profile_path = (ROOT / "profiles" / (config["profile"] + ".json")).resolve()
    if profile_path.parent != (ROOT / "profiles").resolve():
        raise ValueError("Invalid profile identifier")
    profile = json.loads(profile_path.read_text("utf8"))
    rows = json.loads((locale / "strings.json").read_text("utf8"))
    importer = importlib.import_module("tools.import.int_files")
    pending = importer.validate_rows(rows, config)
    if args.strict and (pending or any(r.get("status") != "reviewed" for r in rows)):
        raise ValueError(
            "Strict validation requires all entries translated and reviewed"
        )
    if args.game_dir:
        from tools.build.pipeline import check_originals

        check_originals(args.game_dir, profile)
        if args.command != "extract":
            importer.verify_sources(args.game_dir / "System", rows)
    if args.command == "validate":
        if args.font:
            from tools.validate.fonts import check_font

            check_font(rows, args.font, config["font"])
        print(
            f"VALIDATE PASS: {len(rows)} entries; {pending} untranslated; "
            f'{sum(r.get("status") != "reviewed" for r in rows)} unreviewed'
        )
        return 0
    if not args.game_dir:
        raise ValueError(
            "--game-dir must point to an unmodified supported GOG installation"
        )
    out = (args.out or ROOT / "build" / args.locale).resolve()
    if out == args.game_dir.resolve() or out.is_relative_to(args.game_dir.resolve()):
        raise ValueError("Output must be outside the original game directory")
    if args.command == "extract":
        from tools.extract.catalog import export

        export(args.game_dir / "System", out)
        return 0
    if not args.font:
        raise ValueError("--font is required; fonts are not bundled")
    from tools.build.pipeline import build

    build(args.game_dir, out, rows, config, profile, args.font)
    return 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf8")
    try:
        sys.exit(main())
    except (ValueError, KeyError, OSError, AssertionError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
