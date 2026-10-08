import tempfile
from pathlib import Path
import unittest
from tools.validate.documentation_links import links, anchors, audit

class DocumentationLinkTests(unittest.TestCase):
    def test_balanced_parentheses_and_titles(self):
        self.assertEqual(list(links('[wiki](https://example.test/Page_(game)) [doc](doc.md "title")')), ['https://example.test/Page_(game)', 'doc.md'])

    def test_reference_links_and_code_exclusion(self):
        self.assertEqual(list(links('```text\n[not link](missing.md)\n```\n[x]: target.md\n<https://example.test/>')), ['target.md','https://example.test/'])

    def test_duplicate_and_chinese_headings(self):
        self.assertEqual(anchors('# 当前状态\n## 当前状态\n## A B'), {'当前状态','当前状态-1','a-b'})

    def test_missing_file_and_anchor_are_reported(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            (root/'README.md').write_text('# 首页\n[ok](guide.md#安装)\n[bad](missing.md)\n[anchor](guide.md#不存在)',encoding='utf8')
            (root/'guide.md').write_text('# 安装',encoding='utf8')
            result=audit(root)
            self.assertEqual(len(result['local_errors']),2)
            self.assertEqual({x['reason'] for x in result['local_errors']},{'missing target','missing heading anchor'})

if __name__=='__main__': unittest.main()
