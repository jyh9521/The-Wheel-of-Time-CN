import unittest
from tools.font.scale_package_fonts import scaled,restore,sha,choose_cpp
class FontScalingTests(unittest.TestCase):
 def test_scaled_metrics(self):
  self.assertEqual([scaled(n,1.5)for n in [0,7,8,14,15,30]],[0,11,12,21,23,45])
 def test_three_times_is_from_baseline(self):
  self.assertEqual([scaled(n,3)for n in [7,8,14,15,30]],[21,24,42,45,90])
 def test_mixed_size_page_capacity(self):
  self.assertEqual([choose_cpp(c)for c in [100,16,9,4,3,1]],[16,16,8,4,2,1])
  with self.assertRaisesRegex(ValueError,'256px'):choose_cpp(0)
 def test_restore_hash_guard(self):
  with self.assertRaisesRegex(ValueError,'Modified package'):restore(b'changed',dict(modified_sha256=sha(b'other')))
 def test_append_only_rollback(self):
  old=bytes(range(128))+b'original body';modified=bytes(128)+old[128:]+b'appended texture'
  report=dict(modified_sha256=sha(modified),original_size=len(old),header_before=old[:128].hex(),original_sha256=sha(old))
  self.assertEqual(restore(modified,report),old)
  report['original_sha256']=sha(b'unknown')
  with self.assertRaisesRegex(ValueError,'Rollback hash'):restore(modified,report)
