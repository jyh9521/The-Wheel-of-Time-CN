import unittest
from pathlib import Path
from tools.validate.terminology import load_terms
from tools.pack.movie_text import read_translations, wrap

ROOT = Path(__file__).resolve().parents[1]

class ReferenceTermsTests(unittest.TestCase):
    def test_reference_overrides(self):
        terms = dict(load_terms(ROOT / 'GLOSSARY.md', '中文译名'))
        for source, target in {'al\'Lan Mandragoran':'岚', 'Moiraine Damodred':'沐瑞', 'Aridhol':'爱瑞荷', 'Forsaken':'背弃者', 'Tam al\'Thor':'谭姆·亚瑟', 'Loial':'罗亚尔', 'Elaida':'爱莉达'}.items():
            self.assertEqual(terms.get(source), target, source)

    def test_fmv_name_spaces(self):
        for path in (ROOT / 'locales/zh-CN/fmv').glob('*.tsv'):
            for index, text in read_translations(path).items():
                self.assertNotIn(' 里斯琳', text, (path.name, index))
                self.assertNotIn('里斯琳 ', text, (path.name, index))
                wrap(text)

    def test_intro_reference(self):
        rows = read_translations(ROOT / 'locales/zh-CN/fmv/Intro.tsv')
        self.assertEqual(''.join(rows[i] for i in (1,2,3,4)), '时光之轮旋转不息，岁月来去如风，世代更替只留下回忆；时间流淌，残留的回忆变为传说，传说又慢慢成为神话，而当同一纪元轮回再临时，神话也早已烟消云散。')

if __name__ == '__main__':
    unittest.main()
