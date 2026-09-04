param(
    [switch]$Clean,
    [switch]$Zip,
    [switch]$InstallDependencies,
    [switch]$RequireClean,
    [string]$ExpectedCommit,
    [string]$ExpectedTag,
    [ValidateSet("Optional", "Required")][string]$SigningMode = "Optional"
)
$ErrorActionPreference = "Stop"
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $RepoRoot
function Invoke-Native {
    param([string]$FilePath, [string]$Description, [string[]]$Arguments)
    & $FilePath @Arguments
    if ($LASTEXITCODE -ne 0) { throw "$Description failed with exit code $LASTEXITCODE." }
}
if ($env:VIRTUAL_ENV) { $Python = (Get-Command python -ErrorAction Stop).Source }
else { $Python = Join-Path $RepoRoot '.venv\Scripts\python.exe' }
if ($InstallDependencies) { & "$PSScriptRoot\install_locked_dependencies.ps1" -Python $Python }
if ($RequireClean -and (& git status --porcelain)) { throw 'Release build requires a clean working tree.' }
$HeadCommit = (& git rev-parse HEAD).Trim()
if ($ExpectedCommit -and $HeadCommit -ne $ExpectedCommit) { throw 'Source SHA mismatch.' }
$MetadataArguments = @("$PSScriptRoot\release_metadata.py")
if ($ExpectedTag) { $MetadataArguments += @('--expected-tag', $ExpectedTag) }
$MetadataJson = & $Python @MetadataArguments
if ($LASTEXITCODE -ne 0) { throw 'Release metadata validation failed.' }
$Metadata = $MetadataJson | ConvertFrom-Json
$SourceDateEpoch = (& git show -s --format=%ct HEAD).Trim()
$Dotnet = if ($env:AEGISVAULT_DOTNET) { $env:AEGISVAULT_DOTNET } else { (Get-Command dotnet -ErrorAction Stop).Source }
$Bundle = Join-Path $RepoRoot 'dist\AegisVault'
# Clean only generated application output, never the workspace or shared toolchains.
if ($Clean -and (Test-Path -LiteralPath $Bundle)) {
    $Resolved = (Resolve-Path -LiteralPath $Bundle).Path
    if ($Resolved -ne (Join-Path $RepoRoot 'dist\AegisVault')) { throw 'Invalid clean target.' }
    Remove-Item -LiteralPath $Resolved -Recurse -Force
}
New-Item -ItemType Directory -Force -Path $Bundle,(Join-Path $RepoRoot 'build') | Out-Null
Invoke-Native $Python 'backend version resource' @("$PSScriptRoot\generate_version_info.py", '--output', 'build/aegisvault-version-info.txt')
$PreviousPythonHashSeed = $env:PYTHONHASHSEED
$PreviousEpoch = $env:SOURCE_DATE_EPOCH
$PreviousPath = $env:PATH
$PythonBase = (& $Python -c 'import sys; print(sys.base_prefix)').Trim()
try {
    $env:PYTHONHASHSEED = "0"
    $env:SOURCE_DATE_EPOCH = $SourceDateEpoch
    $env:PATH = @((Split-Path -Parent $Python), $PythonBase, "$PythonBase\DLLs", "$env:SYSTEMROOT\System32", $env:SYSTEMROOT) -join [IO.Path]::PathSeparator
    Invoke-Native $Python 'backend packaging' @('-m', 'PyInstaller', '--clean', '--noconfirm', '--distpath', 'build/backend-dist', 'scripts/aegisvault.spec')
} finally {
    $env:PYTHONHASHSEED = $PreviousPythonHashSeed
    $env:SOURCE_DATE_EPOCH = $PreviousEpoch
    $env:PATH = $PreviousPath
}
Invoke-Native $Python 'backend input audit' @('scripts/audit_build_inputs.py', '--analysis-toc', 'build/aegisvault/Analysis-00.toc')
Invoke-Native $Dotnet 'WinUI x64 Release publish' @('publish', 'src/AegisVault.App/AegisVault.App.csproj', '-c', 'Release', '-p:Platform=x64', '-p:RestoreLockedMode=true', '-warnaserror', '-o', $Bundle)
New-Item -ItemType Directory -Force -Path "$Bundle\backend" | Out-Null
Copy-Item -LiteralPath 'build/backend-dist/AegisVault.Backend.exe' -Destination "$Bundle\backend\AegisVault.Backend.exe"
$ExecutablePath = Join-Path $Bundle $Metadata.exe_name
foreach ($Executable in @($ExecutablePath, "$Bundle\backend\AegisVault.Backend.exe")) {
    & "$PSScriptRoot\sign_windows_artifact.ps1" -Executable $Executable -SigningMode $SigningMode
}
& "$PSScriptRoot\smoke_packaged.ps1" -Executable $ExecutablePath
if ($Zip) {
    $ZipPath = Join-Path $RepoRoot ("dist\{0}" -f $Metadata.zip_name)
    Invoke-Native $Python 'deterministic folder ZIP' @('scripts/package_windows.py', '--directory', $Bundle, '--output', $ZipPath, '--source-date-epoch', $SourceDateEpoch)
    $SbomPath = Join-Path $RepoRoot ("dist\{0}" -f $Metadata.sbom_name)
    Invoke-Native $Python 'combined runtime SBOM' @('scripts/generate_sbom.py', '--requirements', 'requirements.lock', '--executable', $ExecutablePath, '--zip', $ZipPath, '--output', $SbomPath, '--source-date-epoch', $SourceDateEpoch)
    Invoke-Native $Python 'checksums' @('scripts/generate_checksums.py', '--output', 'dist/SHA256SUMS', $ZipPath, $SbomPath)
}
$AuditArguments = @('scripts/audit_release_artifacts.py', '--dist', 'dist', '--signing-mode', $SigningMode)
if (-not $Zip) { $AuditArguments += '--executable-only' }
Invoke-Native $Python 'release bundle audit' $AuditArguments
Write-Host "WinUI package: $ExecutablePath"
