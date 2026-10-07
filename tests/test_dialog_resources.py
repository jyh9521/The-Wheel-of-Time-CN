import struct
import unittest
from tools.pack.dialog_resources import transform
from tools.build.package_overlay_test import configure


class DialogResourcesTests(unittest.TestCase):
    def dialog(self, extended):
        # One button; no menu or class, UTF-16 title, preserved font metrics.
        if extended:
            b=bytearray(struct.pack('<HHIIIHhhhh',1,65535,0,0,64,1,0,0,180,90))
        else:
            b=bytearray(struct.pack('<IIHhhhh',64,0,1,0,0,180,90))
        b+=b'\0\0'*3
        b+=struct.pack('<HHBB',8,400,0,1) if extended else struct.pack('<H',8)
        b+='MS Sans Serif\0'.encode('utf-16le')
        b+=b'\0'*((-len(b))%4)
        b+=struct.pack('<IIIhhhhI',0,0,0,10,20,40,15,100) if extended else struct.pack('<IIhhhhH',0,0,10,20,40,15,100)
        b+=struct.pack('<HH',65535,128)+'&Next >\0'.encode('utf-16le')+b'\0\0'
        return bytes(b)

    def test_both_template_formats_round_trip(self):
        for extended in (True,False):
            original=self.dialog(extended)
            translated,rows=transform(original,{'&Next >':'下一步(&N) >'})
            self.assertEqual(rows,[{'before':'&Next >','after':'下一步(&N) >'}])
            restored,_=transform(translated,{'下一步(&N) >':'&Next >'})
            self.assertEqual(restored,original)

    def test_untranslated_dialog_is_identical(self):
        for extended in (True,False):
            original=self.dialog(extended)
            self.assertEqual(transform(original,{})[0],original)

    def test_config_changes_only_requested_section(self):
        original=b'[Other]\r\nbSubtitles=False\r\n[WOT.WOTPlayer]\r\nbSubtitles=False\r\nName=Default\r\n'
        modified=configure(original,{'WOT.WOTPlayer':{'bSubtitles':'True'}})
        self.assertEqual(modified,b'[Other]\r\nbSubtitles=False\r\n[WOT.WOTPlayer]\r\nbSubtitles=True\r\nName=Default\r\n')

    def test_utf16_preserved(self):
        original='[Player]\r\nName=测试\r\n'.encode('utf-16')
        modified=configure(original,{'Player':{'Option':'True'}})
        self.assertTrue(modified.startswith(b'\xff\xfe'))
        self.assertIn('Name=测试',modified.decode('utf-16'))


if __name__=='__main__':unittest.main()
