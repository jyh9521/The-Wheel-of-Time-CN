import unittest
from tools.validate.hardware_settings import field,repaired
P=dict(section='WinDrv.WindowsClient',key='MasterDetailLevel',allowed=[0,1,2],recovery_value=2)
class HardwareSettingsTests(unittest.TestCase):
 def test_only_invalid_field_changes(self):
  old=b'[Other]\r\nMasterDetailLevel=255\r\n[WinDrv.WindowsClient]\r\nMasterDetailLevel=255 ; saved\r\nMaxDetailLevel=255\r\n'
  new=repaired(old,P)
  self.assertEqual(new,old.replace(b'MasterDetailLevel=255 ; saved',b'MasterDetailLevel=2 ; saved'))
 def test_valid_selectors_not_reset(self):
  for n in [0,1,2]:
   data=f'[WinDrv.WindowsClient]\nMasterDetailLevel={n}\n'.encode()
   self.assertEqual(field(data,P)[0],n)
   with self.assertRaisesRegex(ValueError,'already valid'):repaired(data,P)
 def test_duplicate_keys_rejected(self):
  with self.assertRaises(ValueError):field(b'[WinDrv.WindowsClient]\nMasterDetailLevel=2\nMasterDetailLevel=255\n',P)
 def test_duplicate_section_rejected(self):
  with self.assertRaises(ValueError):field(b'[WinDrv.WindowsClient]\nMasterDetailLevel=255\n[WinDrv.WindowsClient]\n',P)
 def test_missing_field_rejected(self):
  with self.assertRaises(ValueError):field(b'[Other]\nMasterDetailLevel=255\n',P)
