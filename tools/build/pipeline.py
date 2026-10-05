import hashlib
import importlib
import json
import platform
import sys
import shutil
import tempfile
from pathlib import Path
import PIL
import fontTools
from src.patch.delta import create, apply, sha
from tools.font.build_font import build as build_font
from tools.validate.fonts import check_font
from src.patch.resource_fields import apply_resource_edits


def check_originals(game, profile):
    for name, expected in (
        profile["files"] | profile.get("read_only_inputs", {})
    ).items():
        path = game / name
        data = path.read_bytes()
        if len(data) != expected["size"] or sha(data) != expected["sha256"]:
            raise ValueError("Unsupported or modified original: " + name)


def build(
    game, out, rows, config, profile, fontpath, source_dir=None, source_report=None
):
    source_dir = source_dir or game / "System"
    check_originals(game, profile)
    texts = [r["translation"] for r in rows if r.get("translation")]
    if config.get("credits_data"):
        texts += [r["translation"] for r in config["credits_data"]["rows"]]
    if config.get("key_names_data"):
        texts += list(config["key_names_data"].values())
    if config.get("tutorial_prompts_data"):
        texts += [r["translation"] for r in config["tutorial_prompts_data"]["rows"]]
    if config.get('map_prompts_data'):
        texts += [r['translation'] for m in config['map_prompts_data']['maps'] for r in m['rows']]
    if config.get("native_ui_data"):
        texts += [r["translation"] for r in config["native_ui_data"]["strings"]]
        texts += [
            t
            for r in config["native_ui_data"]["preferences"]
            for t in r["translations"].values()
        ]
    if source_report:
        from tools.build.source_layer import active_subtitle_texts

        texts += active_subtitle_texts(source_dir, rows, profile["subtitle_files"])
    check_font([{"translation": text} for text in texts], fontpath, config["font"])
    out.mkdir(parents=True, exist_ok=True)
    resources = out / "resources" / "System"
    if not resources.resolve().is_relative_to(out.resolve()):
        raise ValueError("Resource directory escapes output")
    resources.mkdir(parents=True, exist_ok=True)
    for path in [
        resources / "WOT.u",
        out / "FONT_DIFF.json",
        out / "PATCH.json",
        out / "BUILD_REPORT.json",
    ]:
        if not path.resolve().is_relative_to(out.resolve()):
            raise ValueError("Artifact path escapes output")
    unknown = {
        r["file"]
        for r in rows
        if r.get("translation") and "System/" + r["file"] not in profile["files"]
    }
    if unknown:
        raise ValueError(
            "Resource not in verified profile: " + ", ".join(sorted(unknown))
        )
    timing = importlib.import_module("tools.import.int_files").import_rows(
        source_dir, rows, resources, config, profile
    )
    native_ui = None
    if config.get("native_ui_data"):
        native_ui = importlib.import_module("tools.import.preferences").build(
            source_dir, resources, config["native_ui_data"], config, profile
        )
    if source_report:
        for name in profile["subtitle_files"]:
            if not (resources / name).exists():
                shutil.copyfile(source_dir / name, resources / name)
    if any(ord(c) >= 256 for s in texts for c in s):
        font_result = build_font(
            game / "System/WOT.u",
            resources / "WOT.u",
            texts,
            fontpath,
            out / "FONT_DIFF.json",
            profile,
            config["font"],
        )
    else:
        shutil.copyfile(game / "System/WOT.u", resources / "WOT.u")
        font_result = {
            "unique_glyphs": 0,
            "reason": "legacy font coverage; package unchanged",
        }
        (out / "FONT_DIFF.json").write_text(json.dumps(font_result), "utf8")
    resource_edits = apply_resource_edits(resources / "WOT.u", profile)
    texture_labels = None
    if config.get("texture_labels_data"):
        from tools.font.build_texture_labels import build as build_texture_labels

        with tempfile.TemporaryDirectory(prefix="texture-labels-", dir=out) as temp:
            source = Path(temp) / "WOT.u"
            shutil.copyfile(resources / "WOT.u", source)
            texture_labels = build_texture_labels(
                source,
                resources / "WOT.u",
                fontpath,
                config["texture_labels_data"],
                profile["texture_labels"],
                out / "TEXTURE_LABEL_DIFF.json",
                config["font"].get("collection_index", 0),
            )
    from src.patch.display_expressions import apply_display_expressions

    display_expressions = apply_display_expressions(
        resources / "WOT.u", profile, out / "MENU_VALUE_DIFF.json"
    )
    key_display = None
    if config.get("key_names_data"):
        if not (resources / "WoT.int").exists():
            shutil.copyfile(source_dir / "WoT.int", resources / "WoT.int")
        from src.patch.key_display import apply as apply_key_display

        key_display = apply_key_display(
            resources / "WOT.u",
            config["key_names_data"],
            profile["key_display"],
            out / "KEY_DISPLAY_DIFF.json",
        )
    credits = None
    if config.get("credits_data"):
        from src.patch.credits import apply as apply_credits

        terminology = None
        if config.get("terminology"):
            from tools.validate.terminology import load_terms

            glossary = (
                Path(__file__).resolve().parents[2] / config["terminology"]["path"]
            )
            terminology = load_terms(glossary, config["terminology"]["target_column"])
        credits = apply_credits(
            resources / "WOT.u",
            config["credits_data"],
            profile,
            out / "CREDITS_DIFF.json",
            terminology,
        )
    native_properties = None
    if config.get("native_properties_data"):
        from src.patch.native_properties import build as build_native_properties

        native_properties = build_native_properties(
            game / "System/Window.dll",
            resources / "Window.dll",
            config["native_properties_data"],
            profile["native_properties"],
            out / "NATIVE_DISPLAY_DIFF.json",
        )
    if source_report:
        source_report = dict(source_report, production_build_integrated=True)
    names = sorted(
        {"System/" + r["file"] for r in rows if r.get("translation")} | {"System/WOT.u"}
    )
    if config.get('map_prompts_data'):
        from src.patch.map_prompts import build as build_map_prompts
        map_reports = {}
        for spec in config['map_prompts_data']['maps']:
            name = spec['file']
            if name not in profile['files'] or profile['files'][name]['sha256'] != spec['sha256']:
                raise ValueError('Map prompt profile identity mismatch')
            map_reports[name] = build_map_prompts(game/name, out/'resources'/name, spec)
        names = sorted(set(names) | set(map_reports))
        (out/'MAP_PROMPTS_DIFF.json').write_text(json.dumps(map_reports,indent=2)+'\n',encoding='utf8')
    if native_ui:
        names = sorted(set(names) | {"System/" + n for n in native_ui["files"]})
    if key_display:
        names = sorted(set(names) | {"System/WoT.int"})
    if native_properties:
        names = sorted(set(names) | {"System/Window.dll"})
    if source_report:
        names = sorted(set(names) | {"System/" + n for n in profile["subtitle_files"]})
    subtitle_display = None
    additions = []
    if config.get('subtitle_display'):
        from tools.build.subtitle_display import build as build_subtitle_display
        subtitle_display = build_subtitle_display(game, resources/'WOT.u', fontpath, out/'subtitle-display', config)
        additions = ['System/SubtitleRuntime.u', 'System/SubtitleRuntime.int']
        names = sorted(set(names) | set(additions))
    files = {}
    for name in names:
        if name not in profile["files"] and name not in additions:
            raise ValueError("Resource not in verified profile: " + name)
        b = b"" if name in additions else (game / name).read_bytes()
        m = (out / "resources" / name).read_bytes()
        d = create(b, m)
        if apply(b, d) != m:
            raise ValueError("Delta roundtrip failed")
        files[name] = d
    bundle = {
        "format": "localization-bundle-v1",
        "locale": config["locale"],
        "profile": profile["id"],
        "files": files,
        "owned_additions": additions,
    }
    (out / "PATCH.json").write_text(json.dumps(bundle, separators=(",", ":")), "utf8")
    report = {
        "locale": config["locale"],
        "profile": profile["id"],
        "timing": timing,
        "subtitle_display": subtitle_display,
        "font_sha256": sha(fontpath.read_bytes()),
        "font_collection_index": config["font"].get("collection_index", 0),
        "font_redistribution": "not authorized by build; check font license before release",
        "environment": {
            "python": platform.python_version(),
            "pillow": PIL.__version__,
            "fonttools": fontTools.__version__,
        },
        "input_config_sha256": sha(
            json.dumps(config, sort_keys=True, ensure_ascii=False).encode()
        ),
        "input_rows_sha256": sha(
            json.dumps(rows, sort_keys=True, ensure_ascii=False).encode()
        ),
        "files": {
            n: {
                k: d[k]
                for k in (
                    "original_sha256",
                    "original_size",
                    "modified_sha256",
                    "modified_size",
                )
            }
            for n, d in files.items()
        },
        "modified_file": "resources/System/WOT.u",
        "diff_file": "FONT_DIFF.json",
        "originals_unchanged": True,
        "resource_edits": resource_edits,
        "texture_labels": texture_labels,
        "native_ui": native_ui,
        "display_expressions": display_expressions,
        "key_display": key_display,
        "credits": credits,
        "native_properties": native_properties,
        "subtitle_source": source_report,
        "bytecode_unchanged": not bool(
            resource_edits or display_expressions or credits
        ),
        "font_diff_scope": "Font generation stage, before display-only resource field edits",
    }
    check_originals(game, profile)
    (out / "BUILD_REPORT.json").write_text(json.dumps(report, indent=2), "utf8")
    print(
        f'BUILD PASS: locale={config["locale"]}; {len(files)} files; '
        f'{font_result["unique_glyphs"]} glyphs/font; delta roundtrip PASS; originals unchanged'
    )
