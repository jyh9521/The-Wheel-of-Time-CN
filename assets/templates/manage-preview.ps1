param(
    [Parameter(Mandatory=$true)][string]$GameDir,
    [ValidateSet("apply","verify","restore")][string]$Command="apply"
)
$ErrorActionPreference="Stop"
& python -X utf8 (Join-Path $PSScriptRoot "install.py") $Command --bundle (Join-Path $PSScriptRoot "PATCH.json") --target $GameDir
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
