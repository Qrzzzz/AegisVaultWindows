param([Parameter(Mandatory=$true)][string]$Executable)
$ErrorActionPreference = 'Stop'
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$Python = if ($env:VIRTUAL_ENV) { (Get-Command python).Source } else { Join-Path $RepoRoot '.venv\Scripts\python.exe' }
$Frontend = (Resolve-Path -LiteralPath $Executable).Path
$Backend = Join-Path (Split-Path -Parent $Frontend) 'backend\AegisVault.Backend.exe'
& $Python "$PSScriptRoot\smoke_backend.py" --executable $Backend
if ($LASTEXITCODE -ne 0) { throw 'Packaged backend smoke failed.' }
# Native UI interaction is exercised separately by test_winui.ps1 in an interactive desktop.
