import json
from pathlib import Path
import re
import unittest

ROOT=Path(__file__).resolve().parents[1]


class PortableInstallerTests(unittest.TestCase):
    def test_ui_strings_are_locale_data(self):
        source=(ROOT/'src/installer/PortableInstaller.cs').read_text('utf-8')
        data=json.loads((ROOT/'locales/zh-CN/installer-ui.json').read_text('utf-8'))
        keys=set(re.findall(r'Ui.T\("([a-z_]+)"\)',source))
        self.assertTrue(keys)
        self.assertFalse(keys-set(data))
        self.assertFalse(re.search(r'[\u4e00-\u9fff]',source))

    def test_native_ui_no_install_registration_or_shortcuts(self):
        source=(ROOT/'src/installer/PortableInstaller.cs').read_text('utf-8')
        for api in ('Microsoft.Win32.Registry','RegSetValue','CreateShortcut','msiexec','unins000'):
            self.assertNotIn(api,source)
        self.assertIn('start.CreateNoWindow = true',source)
        self.assertIn('checkedPath != game',source)
        self.assertIn('install.Enabled = false',source)
        self.assertIn('"-NoProfile -NonInteractive -ExecutionPolicy Bypass -File "',source)

    def test_material_ui_retains_native_keyboard_and_accessibility(self):
        source=(ROOT/'src/installer/PortableInstaller.cs').read_text('utf-8')
        for marker in ('class MaterialButton : Button', 'SystemInformation.HighContrast',
                       'ShowFocusCues', 'AutoScaleMode = AutoScaleMode.Font',
                       'AcceptButton = check', 'Ui.T("directory_title")'):
            self.assertIn(marker, source)
        self.assertNotIn('WebView', source)

    def test_ui_errors_do_not_depend_on_system_language(self):
        source=(ROOT/'src/installer/PortableInstaller.cs').read_text('utf-8')
        for leaked in ('ex.Message', 'MessageBox.Show', 'FolderBrowserDialog', 'log.AppendText(result ', 'log.AppendText(verified)'):
            self.assertNotIn(leaked, source)
        for marker in ('Ui.Bootstrap()', 'Ui.Error(ex)', 'Ui.BackendError(result)', 'class DirectoryPicker', 'Ui.T("cancel")'):
            self.assertIn(marker, source)

    def test_file_results_are_structured_and_localized(self):
        source=(ROOT/'src/installer/PortableInstaller.cs').read_text('utf-8')
        backend=(ROOT/'assets/templates/player-test.ps1').read_text('utf-8')
        data=json.loads((ROOT/'locales/zh-CN/installer-ui.json').read_text('utf-8'))
        self.assertIn('Ui.BackendReport(result)',source)
        self.assertIn('FILE_RESULT ',source)
        self.assertIn('CHECK FAILED: files=',backend)
        self.assertIn('$failures++',backend)
        for reason in ('pass','installed','ready','missing','hash_mismatch','readonly','access','addition_exists','backup_package'):
            self.assertIn('file_'+reason,data)
        self.assertIn('if (action == "check" || exit != 0)',source)
        self.assertIn('Backup belongs to another package',source)

    def test_attribution_link_is_locale_data(self):
        source=(ROOT/'src/installer/PortableInstaller.cs').read_text('utf-8')
        data=json.loads((ROOT/'locales/zh-CN/installer-ui.json').read_text('utf-8'))
        self.assertIn('var attribution = new LinkLabel',source)
        self.assertIn('TextAlign = ContentAlignment.MiddleRight',source)
        self.assertIn('attribution.LinkClicked += delegate',source)
        self.assertEqual(data['attribution_url'],'https://blog.blfy.cc/')
        self.assertIn('伯翎飞云',data['attribution_text'])
        self.assertNotIn('blog.blfy.cc',source)

    def test_preflight_is_independent_of_apply(self):
        source=(ROOT/'assets/templates/player-test.ps1').read_text('utf-8')
        block=source.split("if ($Action -eq 'check')",1)[1].split("if ($Action -eq 'verify'",1)[0]
        for writing in ('Put $','WriteAllBytes','CreateDirectory','Set-Content','CopyFile'):
            self.assertNotIn(writing,block)
        self.assertIn('AssertWritable',block)
        self.assertIn('no game files written',block)


if __name__=='__main__':unittest.main()
