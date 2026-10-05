import unittest
from tools.build.launcher import portable_launcher
class PortableLauncherTests(unittest.TestCase):
 def test_hash_module_removed_and_verification_preserved(self):
  src="""$ErrorActionPreference = 'Stop'
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
if ((Get-FileHash -LiteralPath (Join-Path $here 'System/WinDrv.dll')).Hash.ToLowerInvariant() -ne $m.dll_sha256) { throw 'Hash mismatch' }
Push-Location (Join-Path $here 'System')
try { & .\\WoT.exe } finally { Pop-Location }
"""
  new=portable_launcher(src)
  self.assertNotIn('Get-FileHash',new)
  self.assertIn('ComputeHash($stream)',new)
  self.assertIn("throw 'Hash mismatch'",new)
  self.assertIn('param([switch]$VerifyOnly)',new)
  self.assertIn('WoT.exe } finally { Pop-Location }',new)
  self.assertEqual(portable_launcher(new),new)
 def test_windows_line_endings(self):
  new=portable_launcher("$ErrorActionPreference = 'Stop'\r\nPush-Location (Join-Path $here 'System')\r\n")
  self.assertIn("function Get-ResourceSha256",new)
  self.assertIn("param([switch]$VerifyOnly)",new)
  self.assertNotIn("\r\n",new)
 def test_unknown_template_rejected(self):
  with self.assertRaises(ValueError):portable_launcher('unknown')
