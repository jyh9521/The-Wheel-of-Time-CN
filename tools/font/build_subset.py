"""Build a reproducible, renamed font subset from locale FMV translations."""
import argparse
import hashlib
import json
from pathlib import Path
from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont
from fontTools import subset
from tools.pack.movie_text import read_translations


def sha(data):
    return hashlib.sha256(data).hexdigest()


def build(source, translations, output, family, license_path, weight=400, code_page_mask=None):
    if code_page_mask is not None and not 0 <= code_page_mask <= 0xffffffff:
        raise ValueError('Invalid code-page mask')
    if output.exists():
        raise ValueError('Choose a new output font')
    if not family.isascii() or not family.isalnum():
        raise ValueError('Family name must be ASCII alphanumeric')
    codepoints = set(range(32, 127))
    inputs = {}
    for path in sorted(translations.glob('*.tsv')):
        inputs[path.name] = sha(path.read_bytes())
        for text in read_translations(path).values():
            codepoints.update(map(ord, text))
    if not inputs:
        raise ValueError('No translation inputs')
    font = TTFont(source, recalcTimestamp=False)
    missing = codepoints - set(font.getBestCmap())
    if missing:
        raise ValueError('Missing glyphs: ' + ','.join('U+%04X' % c for c in sorted(missing)))
    if 'fvar' in font:
        axes = {a.axisTag: (weight if a.axisTag == 'wght' else a.defaultValue)
                for a in font['fvar'].axes}
        font = instantiateVariableFont(font, axes, inplace=True)
    opts = subset.Options()
    opts.recalc_timestamp = False
    # Legacy QuickTime derives script/charset from OS/2 code-page flags.
    opts.prune_codepage_ranges = code_page_mask is None
    opts.name_IDs = ['*']
    opts.name_legacy = True
    opts.name_languages = ['*']
    cutter = subset.Subsetter(options=opts)
    cutter.populate(unicodes=codepoints)
    cutter.subset(font)
    if code_page_mask is not None:
        font['OS/2'].ulCodePageRange1 = code_page_mask
        font['OS/2'].ulCodePageRange2 = 0
    names = {1: family, 2: 'Regular', 3: family + '-Regular-1', 4: family,
             6: family + '-Regular', 16: family, 17: 'Regular', 18: family,
             21: family, 22: 'Regular', 25: family}
    for record in font['name'].names:
        if record.nameID in names:
            record.string = names[record.nameID].encode(record.getEncoding())
    for platform, encoding, language in [(3, 1, 0x409), (1, 0, 0)]:
        for name_id, value in names.items():
            font['name'].setName(value, name_id, platform, encoding, language)
    license_output=output.with_name('OFL.txt')
    if license_output.exists() and license_output.read_bytes()!=license_path.read_bytes():
        raise ValueError('Existing font-directory license differs')
    output.parent.mkdir(parents=True, exist_ok=True)
    font.save(output, reorderTables=True)
    check = TTFont(output, recalcTimestamp=False)
    if codepoints - set(check.getBestCmap()) or 'fvar' in check:
        raise ValueError('Subset readback failed')
    manifest = dict(source_sha256=sha(source.read_bytes()), font_sha256=sha(output.read_bytes()),
                    family=family, weight=weight, code_page_mask=code_page_mask, codepoints=sorted(codepoints),
                    glyphs=len(check.getGlyphOrder()), size=output.stat().st_size,
                    translation_inputs=inputs, license_sha256=sha(license_path.read_bytes()))
    output.with_suffix('.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2)+'\n', 'utf8')
    output.with_name('OFL.txt').write_bytes(license_path.read_bytes())
    print('FONT SUBSET PASS: %d characters; %d glyphs; %d bytes; family=%s; 0 missing' %
          (len(codepoints), manifest['glyphs'], manifest['size'], family))
    return manifest


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source', type=Path, required=True)
    p.add_argument('--translations', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--family', required=True)
    p.add_argument('--license', type=Path, required=True)
    p.add_argument('--weight', type=int, default=400)
    p.add_argument('--code-page-mask', type=lambda value:int(value,0), default=None)
    a=p.parse_args(); build(a.source,a.translations,a.out,a.family,a.license,a.weight,a.code_page_mask)


if __name__=='__main__':main()
