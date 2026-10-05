"""Keep generated Windows launch scripts independent of PowerShell hash modules."""
PREAMBLE="""param([switch]$VerifyOnly)
$ErrorActionPreference = 'Stop'
function Get-ResourceSha256([string]$Path) {
 $stream = [System.IO.File]::OpenRead($Path)
 $sha = [System.Security.Cryptography.SHA256]::Create()
 try { return [System.BitConverter]::ToString($sha.ComputeHash($stream)).Replace('-', '').ToLowerInvariant() }
 finally { $sha.Dispose(); $stream.Dispose() }
}
"""

def portable_launcher(script):
    script=script.replace("\r\n","\n")
    if 'function Get-ResourceSha256' in script:return script
    if "$ErrorActionPreference = 'Stop'" not in script:raise ValueError('Unknown launcher template')
    script=script.replace("$ErrorActionPreference = 'Stop'\n",PREAMBLE,1)
    script=script.replace('(Get-FileHash -LiteralPath','(Get-ResourceSha256').replace('.Hash.ToLowerInvariant()','')
    script=script.replace("Push-Location (Join-Path $here 'System')","if ($VerifyOnly) { Write-Output 'LAUNCH PRECHECK PASS: all expected hashes matched; no game launch'; return }\nPush-Location (Join-Path $here 'System')")
    return script
