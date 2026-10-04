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
    parser.add_argument("--subtitle-source", type=Path)
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
    if config.get("terminology"):
        from tools.validate.terminology import load_terms

        spec = config["terminology"]
        glossary = (ROOT / spec["path"]).resolve()
        if not glossary.is_relative_to(ROOT):
            raise ValueError("Terminology path escapes repository")
        load_terms(glossary, spec["target_column"])
    if config["locale"] != args.locale:
        raise ValueError("Locale identifier mismatch")
    profile_path = (ROOT / "profiles" / (config["profile"] + ".json")).resolve()
    if profile_path.parent != (ROOT / "profiles").resolve():
        raise ValueError("Invalid profile identifier")
    profile = json.loads(profile_path.read_text("utf8"))
    if config.get("texture_labels"):
        spec = config["texture_labels"]
        data_path = (locale / spec["data"]).resolve()
        labels_profile = (ROOT / "profiles" / spec["profile"]).resolve()
        if data_path.parent != locale or labels_profile.parent != ROOT / "profiles":
            raise ValueError("Texture label configuration path escapes directory")
        config["texture_labels_data"] = json.loads(data_path.read_text("utf8"))
        profile["texture_labels"] = json.loads(labels_profile.read_text("utf8"))
    for field in ('credits', 'native_properties'):
        if config.get(field):
            data_path = (locale / config[field]).resolve()
            if data_path.parent != locale:
                raise ValueError('Locale display data path escapes directory')
            config[field + '_data'] = json.loads(data_path.read_text('utf8'))
    rows = json.loads((locale / "strings.json").read_text("utf8"))
    if config.get("native_ui"):
        native_path = (locale / config["native_ui"]).resolve()
        if native_path.parent != locale:
            raise ValueError("Native UI configuration path escapes locale")
        config["native_ui_data"] = json.loads(native_path.read_text("utf8"))
    importer = importlib.import_module("tools.import.int_files")
    from tools.build.source_layer import source_layer, load_rows, compose_rows

    if args.subtitle_source and not args.game_dir:
        raise ValueError("--subtitle-source requires --game-dir")
    if args.game_dir:
        from tools.build.pipeline import check_originals

        check_originals(args.game_dir, profile)
    manifest = (
        json.loads((ROOT / "profiles/subtitle-source.json").read_text("utf8"))
        if args.subtitle_source
        else {}
    )
    if args.subtitle_source:
        rows = compose_rows(
            rows,
            load_rows(locale, config, manifest),
            load_rows(locale, config, manifest, "subtitle_overrides"),
            manifest,
        )
    with source_layer(args.game_dir or ROOT, args.subtitle_source, manifest) as (
        source_dir,
        source_report,
    ):
        pending = importer.validate_rows(rows, config)
        if config.get("native_ui_data"):
            importer.validate_rows(config["native_ui_data"]["strings"], config)
        if args.strict and (
            pending or any(r.get("status") != "reviewed" for r in rows)
            or (config.get("native_ui_data") and any(
                r.get("status") != "reviewed"
                for r in config["native_ui_data"]["strings"] + config["native_ui_data"]["preferences"]
            ))
        ):
            raise ValueError(
                "Strict validation requires all entries translated and reviewed"
            )
        if args.game_dir:
            from tools.build.pipeline import check_originals

            check_originals(args.game_dir, profile)
            if args.command != "extract":
                importer.verify_sources(source_dir, rows)
                if config.get("native_ui_data"):
                    importer.verify_sources(source_dir, config["native_ui_data"]["strings"])
                    from tools.validate.preferences import verify as verify_preferences
                    verify_preferences(source_dir, config["native_ui_data"])
                if config.get("terminology"):
                    from tools.validate.terminology import validate

                    spec = config["terminology"]
                    glossary = (ROOT / spec["path"]).resolve()
                    if not glossary.is_relative_to(ROOT):
                        raise ValueError("Terminology path escapes repository")
                    validate(rows, source_dir, glossary, spec["target_column"])

        if args.command == "validate":
            if args.font:
                from tools.validate.fonts import check_font

                font_rows = rows
                if source_report:
                    from tools.build.source_layer import active_subtitle_texts

                    font_rows = rows + [
                        {"translation": text}
                        for text in active_subtitle_texts(
                            source_dir, rows, profile["subtitle_files"]
                        )
                    ]
                if config.get("texture_labels_data"):
                    font_rows = font_rows + [
                        {"translation": text}
                        for text in config["texture_labels_data"]["labels"].values()
                    ]
                if config.get("native_ui_data"):
                    font_rows = font_rows + config["native_ui_data"]["strings"] + [
                        {"translation": text}
                        for r in config["native_ui_data"]["preferences"]
                        for text in r["translations"].values()
                    ]
                check_font(font_rows, args.font, config["font"])
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
        if out == args.game_dir.resolve() or out.is_relative_to(
            args.game_dir.resolve()
        ):
            raise ValueError("Output must be outside the original game directory")
        if args.command == "extract":
            from tools.extract.catalog import export

            export(source_dir, out)
            return 0
        if not args.font:
            raise ValueError("--font is required; fonts are not bundled")
        from tools.build.pipeline import build

        build(
            args.game_dir,
            out,
            rows,
            config,
            profile,
            args.font,
            source_dir,
            source_report,
        )
        return 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf8")
    try:
        sys.exit(main())
    except (ValueError, KeyError, OSError, AssertionError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
