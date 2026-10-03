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
    for name, expected in profile['files'].items():
        path = game / name
        data = path.read_bytes()
        if len(data) != expected['size'] or sha(data) != expected['sha256']:
            raise ValueError('Unsupported or modified original: ' + name)


def build(game, out, rows, config, profile, fontpath, source_dir=None, source_report=None):
    source_dir = source_dir or game / 'System'
    check_originals(game, profile)
    texts = [r['translation'] for r in rows if r.get('translation')]
    if source_report:
        from tools.build.source_layer import active_subtitle_texts
        texts += active_subtitle_texts(source_dir, rows, profile['subtitle_files'])
    check_font([{'translation': text} for text in texts], fontpath, config['font'])
    out.mkdir(parents=True, exist_ok=True)
    resources = out / 'resources' / 'System'
    if not resources.resolve().is_relative_to(out.resolve()):
        raise ValueError('Resource directory escapes output')
    resources.mkdir(parents=True, exist_ok=True)
    for path in [resources / 'WOT.u', out / 'FONT_DIFF.json', out / 'PATCH.json', out / 'BUILD_REPORT.json']:
        if not path.resolve().is_relative_to(out.resolve()):
            raise ValueError('Artifact path escapes output')
    unknown = {r['file'] for r in rows if r.get('translation') and 'System/' + r['file'] not in profile['files']}
    if unknown:
        raise ValueError('Resource not in verified profile: ' + ', '.join(sorted(unknown)))
    timing = importlib.import_module('tools.import.int_files').import_rows(
        source_dir, rows, resources, config, profile)
    native_ui = None
    if config.get('native_ui_data'):
        native_ui = importlib.import_module('tools.import.preferences').build(
            source_dir, resources, config['native_ui_data'], config, profile)
    if source_report:
        for name in profile['subtitle_files']:
            if not (resources / name).exists():
                shutil.copyfile(source_dir / name, resources / name)
    if any(ord(c) >= 256 for s in texts for c in s):
        font_result = build_font(game / 'System/WOT.u', resources / 'WOT.u',
                             texts,
                                 fontpath, out / 'FONT_DIFF.json', profile, config['font'])
    else:
        shutil.copyfile(game / 'System/WOT.u', resources / 'WOT.u')
        font_result = {'unique_glyphs': 0, 'reason': 'legacy font coverage; package unchanged'}
        (out / 'FONT_DIFF.json').write_text(json.dumps(font_result), 'utf8')
    resource_edits = apply_resource_edits(resources / 'WOT.u', profile)
    texture_labels = None
    if config.get('texture_labels_data'):
        from tools.font.build_texture_labels import build as build_texture_labels
        with tempfile.TemporaryDirectory(prefix='texture-labels-', dir=out) as temp:
            source = Path(temp) / 'WOT.u'
            shutil.copyfile(resources / 'WOT.u', source)
            texture_labels = build_texture_labels(
                source, resources / 'WOT.u', fontpath, config['texture_labels_data'],
                profile['texture_labels'], out / 'TEXTURE_LABEL_DIFF.json',
                config['font'].get('collection_index', 0))
    if source_report:
        source_report = dict(source_report, production_build_integrated=True)
    names = sorted({'System/' + r['file'] for r in rows if r.get('translation')} | {'System/WOT.u'})
    if native_ui:
        names = sorted(set(names) | {'System/' + n for n in native_ui['files']})
    if source_report:
        names = sorted(set(names) | {'System/' + n for n in profile['subtitle_files']})
    files = {}
    for name in names:
        if name not in profile['files']:
            raise ValueError('Resource not in verified profile: ' + name)
        b = (game / name).read_bytes()
        m = (out / 'resources' / name).read_bytes()
        d = create(b, m)
        if apply(b, d) != m:
            raise ValueError('Delta roundtrip failed')
        files[name] = d
    bundle = {'format': 'localization-bundle-v1', 'locale': config['locale'],
              'profile': profile['id'], 'files': files}
    (out / 'PATCH.json').write_text(json.dumps(bundle, separators=(',', ':')), 'utf8')
    report = {'locale': config['locale'], 'profile': profile['id'], 'timing': timing,
              'font_sha256': sha(fontpath.read_bytes()), 'font_collection_index': config['font'].get('collection_index', 0),
              'font_redistribution': 'not authorized by build; check font license before release',
              'environment': {'python': platform.python_version(), 'pillow': PIL.__version__,
                              'fonttools': fontTools.__version__},
              'input_config_sha256': sha(json.dumps(config, sort_keys=True, ensure_ascii=False).encode()),
              'input_rows_sha256': sha(json.dumps(rows, sort_keys=True, ensure_ascii=False).encode()),
              'files': {n: {k: d[k] for k in ('original_sha256', 'original_size', 'modified_sha256', 'modified_size')}
                        for n, d in files.items()}, 'modified_file': 'resources/System/WOT.u',
              'diff_file': 'FONT_DIFF.json', 'originals_unchanged': True,
              'resource_edits': resource_edits,
              'texture_labels': texture_labels,
              'native_ui': native_ui,
              'subtitle_source': source_report,
              'bytecode_unchanged': not bool(resource_edits),
              'font_diff_scope': 'Font generation stage, before display-only resource field edits'}
    check_originals(game, profile)
    (out / 'BUILD_REPORT.json').write_text(json.dumps(report, indent=2), 'utf8')
    print(f'BUILD PASS: locale={config["locale"]}; {len(files)} files; '
          f'{font_result["unique_glyphs"]} glyphs/font; delta roundtrip PASS; originals unchanged')
