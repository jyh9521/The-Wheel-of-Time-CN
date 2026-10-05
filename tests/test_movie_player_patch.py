import unittest
from unittest.mock import Mock,patch as mock_patch

from src.patch.movie_player import patch,restore,sha
from tools.build.build_fmv_game_probe import configure_1080p


class MoviePlayerPatchTests(unittest.TestCase):
    def setUp(self):
        self.data=b'fixture!'+bytes.fromhex('83c7fd')+b' audio path stays unchanged'
        self.profile=dict(size=len(self.data),sha256=sha(self.data),rva=64663,before='83c7fd',after='33ff90')
        self.pe=Mock();self.pe.get_offset_from_rva.return_value=8

    def test_patch_and_restore_only_selector(self):
        with mock_patch('src.patch.movie_player.pefile.PE',return_value=self.pe):
            changed,manifest=patch(self.data,self.profile)
        self.assertEqual(changed[:8],self.data[:8])
        self.assertEqual(changed[11:],self.data[11:])
        self.assertEqual(changed[8:11],bytes.fromhex('33ff90'))
        self.assertEqual(restore(changed,manifest),self.data)

    def test_unknown_source_rejected(self):
        with self.assertRaisesRegex(ValueError,'version'):
            patch(self.data+b'?',self.profile)

    def test_wrong_expected_opcode_rejected(self):
        self.profile['before']='909090'
        with mock_patch('src.patch.movie_player.pefile.PE',return_value=self.pe):
            with self.assertRaisesRegex(ValueError,'selector bytes'):
                patch(self.data,self.profile)

    def test_modified_identity_required_for_rollback(self):
        with mock_patch('src.patch.movie_player.pefile.PE',return_value=self.pe):
            changed,manifest=patch(self.data,self.profile)
        with self.assertRaises(ValueError):restore(changed+b'?',manifest)

    def test_configuration_preserves_language_audio_and_controls(self):
        text='Language=int\r\nWindowedViewportX=2048\r\nWindowedViewportY=1200\r\nFullscreenViewportX=1920\r\nFullscreenViewportY=1080\r\nStartupFullscreen=True\r\nLanguageExt=itt\r\nMusicVolume=71\r\n'
        result=configure_1080p(text.encode('utf16')).decode('utf16')
        self.assertIn('Language=int\r\n',result)
        self.assertIn('MusicVolume=71\r\n',result)
        self.assertIn('LanguageExt=itt\r\n',result)
        self.assertIn('WindowedViewportX=1920\r\n',result)

    def test_non_english_configuration_rejected(self):
        with self.assertRaisesRegex(ValueError,'English'):
            configure_1080p(b'Language=itt\r\n')

    def test_selector_cpu_semantics(self):
        try:
            from unicorn import Uc,UC_ARCH_X86,UC_MODE_32
            from unicorn.x86_const import UC_X86_REG_EDI,UC_X86_REG_EAX,UC_X86_REG_ESP
        except ImportError:
            self.skipTest('Optional CPU QA requires unicorn')
        for opcode,expected in [('83c7fd',[-3,-2,-1,0,1]),('33ff90',[0]*5)]:
            for index,selected in enumerate(expected):
                emu=Uc(UC_ARCH_X86,UC_MODE_32);emu.mem_map(0x1000,4096)
                emu.mem_write(0x1000,bytes.fromhex(opcode));emu.reg_write(UC_X86_REG_EDI,index)
                emu.reg_write(UC_X86_REG_EAX,0x12345678);emu.reg_write(UC_X86_REG_ESP,0x2000)
                emu.emu_start(0x1000,0x1003)
                self.assertEqual(emu.reg_read(UC_X86_REG_EDI),selected&0xffffffff)
                self.assertEqual(emu.reg_read(UC_X86_REG_EAX),0x12345678)
                self.assertEqual(emu.reg_read(UC_X86_REG_ESP),0x2000)


if __name__=='__main__':unittest.main()
