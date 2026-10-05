"""Documentation structure and confirmed FMV terminology regression checks."""
import re
import unittest
from pathlib import Path
from tools.validate.terminology import load_terms
from tools.pack.movie_text import read_translations

ROOT = Path(__file__).resolve().parents[1]


class PublicDocumentationTests(unittest.TestCase):
    def test_readme_sections_and_progress_links(self):
        text = (ROOT / 'README.md').read_text(encoding='utf-8')
        self.assertEqual(re.findall(r'^## (.+)$', text, re.M), [
            '项目简介', '支持版本与当前状态', '下载', '安装 / 使用', '技术摘要',
            '仓库结构', '从源码重建', '参与翻译 / 添加语言', '译名与翻译参考',
            '已知问题', '更多开发与测试进展', '许可', '致谢'])
        self.assertNotIn('###', text)
        for target in re.findall(r'\]\(([^)#]+)(?:#[^)]*)?\)', text):
            if '://' not in target:
                self.assertTrue((ROOT / target).is_file(), target)

    def test_status_structure_and_internal_links(self):
        path = ROOT / 'docs/STATUS.md'
        text = path.read_text(encoding='utf-8')
        self.assertEqual(re.findall(r'^## (.+)$', text, re.M), [
            '当前总览', '工作区迁移', '菜单与 UI 进展', '字幕专项进展',
            '教程翻译进展', '可选字幕来源进展', '分辨率与显示测试', '待办事项'])
        for target in re.findall(r'\]\(([^)#]+)(?:#[^)]*)?\)', text):
            if '://' not in target:
                self.assertTrue((path.parent / target).is_file(), target)
        self.assertIn('Mission_10 已确认无对白', text)

    def test_fmv_terms_are_in_the_single_parsed_table(self):
        terms = dict(load_terms(ROOT / 'GLOSSARY.md', '中文译名'))
        for source, target in [('Risline', '里斯琳'), ('Dragonmount', '龙山'),
                               ('Whitebridge', '白桥镇'), ('Portal Stone', '传送石'),
                               ("Tarmon Gai'don", '最后战争'), ('Last Battle', '最后战争'),
                               ("Shai'tan", '撒丹'), ('Mistress of Novices', '初阶生师尊')]:
            self.assertEqual(terms[source], target)
        captions = read_translations(ROOT / 'locales/zh-CN/fmv/Mission_04.tsv')
        self.assertEqual([i for i, t in captions.items() if '里斯琳' in t], [30, 36, 39])
        self.assertFalse(any('Risline' in t for t in captions.values()))


if __name__ == '__main__':
    unittest.main()
