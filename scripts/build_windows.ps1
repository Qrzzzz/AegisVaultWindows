param(
    [switch]$Clean,
    [switch]$Zip,
    [switch]$InstallDependencies,
    [switch]$RequireClean,
    [string]$ExpectedCommit,
    [string]$ExpectedTag,
    [ValidateSet("Optional", "Required")]
    [string]$SigningMode = "Optional"
)

$ErrorActionPreference = "Stop"
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $RepoRoot

function Invoke-Native {
    param([string]$FilePath, [string]$Description, [string[]]$Arguments)
    & $FilePath @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "$Description failed with exit code $LASTEXITCODE."
    }
}

function Remove-GeneratedDirectory {
    param([string]$Path)
    $FullPath = [IO.Path]::GetFullPath($Path)
    $RootPrefix = $RepoRoot.TrimEnd([IO.Path]::DirectorySeparatorChar) + [IO.Path]::DirectorySeparatorChar
    if (-not $FullPath.StartsWith($RootPrefix, [StringComparison]::OrdinalIgnoreCase)) {
        throw "Refusing to remove a generated directory outside the repository: $FullPath"
    }
    Remove-Item -LiteralPath $FullPath -Recurse -Force -ErrorAction SilentlyContinue
}

if ($env:VIRTUAL_ENV) {
    $Python = (Get-Command python -ErrorAction Stop).Source
} elseif (Test-Path (Join-Path $RepoRoot ".venv\Scripts\python.exe")) {
    $Python = Join-Path $RepoRoot ".venv\Scripts\python.exe"
} else {
    throw "No virtual environment found. Create one with 'python -m venv .venv'."
}

if ($InstallDependencies) {
    & (Join-Path $PSScriptRoot "install_locked_dependencies.ps1") -Python $Python
}

if ($RequireClean) {
    $Status = (& git -C $RepoRoot status --porcelain=v1 --untracked-files=normal) -join "`n"
    if ($LASTEXITCODE -ne 0) {
        throw "Unable to inspect the Git working tree."
    }
    if (-not [string]::IsNullOrWhiteSpace($Status)) {
        throw "Release build requires a clean working tree:`n$Status"
    }
}

$MetadataArguments = @((Join-Path $PSScriptRoot "release_metadata.py"))
if ($ExpectedTag) {
    $MetadataArguments += @("--expected-tag", $ExpectedTag)
}
$MetadataJson = (& $Python @MetadataArguments) -join "`n"
if ($LASTEXITCODE -ne 0) {
    throw "Release metadata validation failed."
}
$Metadata = $MetadataJson | ConvertFrom-Json

$HeadCommit = (& git -C $RepoRoot rev-parse HEAD).Trim()
if ($LASTEXITCODE -ne 0 -or $HeadCommit -notmatch "^[0-9a-f]{40}$") {
    throw "Unable to resolve the source commit."
}
if ($ExpectedCommit -and $ExpectedCommit.ToLowerInvariant() -ne $HeadCommit.ToLowerInvariant()) {
    throw "Expected commit $ExpectedCommit does not match HEAD $HeadCommit."
}
$SourceDateEpoch = (& git -C $RepoRoot show -s --format=%ct HEAD).Trim()
if ($LASTEXITCODE -ne 0 -or $SourceDateEpoch -notmatch "^\d+$") {
    throw "Unable to resolve SOURCE_DATE_EPOCH from Git."
}

if ($Clean) {
    Remove-GeneratedDirectory (Join-Path $RepoRoot "build")
    Remove-GeneratedDirectory (Join-Path $RepoRoot "dist")
}
[IO.Directory]::CreateDirectory((Join-Path $RepoRoot "build")) | Out-Null
[IO.Directory]::CreateDirectory((Join-Path $RepoRoot "dist")) | Out-Null

$VersionInfo = Join-Path $RepoRoot "build\aegisvault-version-info.txt"
$VersionArguments = @((Join-Path $PSScriptRoot "generate_version_info.py"), "--output", $VersionInfo)
if ($ExpectedTag) {
    $VersionArguments += @("--expected-tag", $ExpectedTag)
}
Invoke-Native $Python "Windows version resource generation" $VersionArguments

$PreviousSourceDateEpoch = $env:SOURCE_DATE_EPOCH
$PreviousPythonHashSeed = $env:PYTHONHASHSEED
$PreviousUtf8 = $env:PYTHONUTF8
$PreviousIoEncoding = $env:PYTHONIOENCODING
$PreviousPath = $env:PATH
$PythonBase = (& $Python -c "import sys; print(sys.base_prefix)").Trim()
if ($LASTEXITCODE -ne 0 -or -not (Test-Path -LiteralPath $PythonBase -PathType Container)) {
    throw "Unable to resolve the base Python runtime for clean PATH construction."
}
$CleanBuildPath = @(
    (Split-Path -Parent $Python),
    $PythonBase,
    (Join-Path $PythonBase "DLLs"),
    (Join-Path $env:SystemRoot "System32"),
    $env:SystemRoot,
    (Join-Path $env:SystemRoot "System32\Wbem")
) | Where-Object { $_ -and (Test-Path -LiteralPath $_ -PathType Container) } | Select-Object -Unique
$BuildLog = New-TemporaryFile
try {
    $env:SOURCE_DATE_EPOCH = $SourceDateEpoch
    $env:PYTHONHASHSEED = "0"
    $env:PYTHONUTF8 = "1"
    $env:PYTHONIOENCODING = "utf-8"
    $env:PATH = $CleanBuildPath -join [IO.Path]::PathSeparator
    & $Python -m PyInstaller --clean --noconfirm (Join-Path $PSScriptRoot "aegisvault.spec") *> $BuildLog
    $BuildStatus = $LASTEXITCODE
    if ($BuildStatus -ne 0) {
        Write-Host "PyInstaller failed. Last log lines:"
        Get-Content -LiteralPath $BuildLog -Tail 120
        exit $BuildStatus
    }
} finally {
    $env:SOURCE_DATE_EPOCH = $PreviousSourceDateEpoch
    $env:PYTHONHASHSEED = $PreviousPythonHashSeed
    $env:PYTHONUTF8 = $PreviousUtf8
    $env:PYTHONIOENCODING = $PreviousIoEncoding
    $env:PATH = $PreviousPath
    Remove-Item -LiteralPath $BuildLog -Force -ErrorAction SilentlyContinue
}
Invoke-Native $Python "PyInstaller input-root audit" @(
    (Join-Path $PSScriptRoot "audit_build_inputs.py"),
    "--analysis-toc", (Join-Path $RepoRoot "build\aegisvault\Analysis-00.toc")
)

$ExecutablePath = Join-Path $RepoRoot ("dist\{0}" -f $Metadata.exe_name)
if (-not (Test-Path -LiteralPath $ExecutablePath -PathType Leaf)) {
    throw "Build completed but executable was not found: $ExecutablePath"
}
& (Join-Path $PSScriptRoot "sign_windows_artifact.ps1") -Executable $ExecutablePath -SigningMode $SigningMode
& (Join-Path $PSScriptRoot "smoke_packaged.ps1") -Executable $ExecutablePath

$AuditArguments = @((Join-Path $PSScriptRoot "audit_release_artifacts.py"), "--dist", (Join-Path $RepoRoot "dist"), "--signing-mode", $SigningMode)
if ($ExpectedTag) {
    $AuditArguments += @("--expected-tag", $ExpectedTag)
}
if (-not $Zip) {
    $AuditArguments += "--executable-only"
    Invoke-Native $Python "Windows executable audit" $AuditArguments
    Write-Host "Build complete: $ExecutablePath"
    return
}

$ZipPath = Join-Path $RepoRoot ("dist\{0}" -f $Metadata.zip_name)
Invoke-Native $Python "deterministic ZIP packaging" @(
    (Join-Path $PSScriptRoot "package_windows.py"), "--executable", $ExecutablePath, "--output", $ZipPath,
    "--source-date-epoch", $SourceDateEpoch
)
$SbomPath = Join-Path $RepoRoot ("dist\{0}" -f $Metadata.sbom_name)
$SbomArguments = @(
    (Join-Path $PSScriptRoot "generate_sbom.py"), "--requirements", (Join-Path $RepoRoot "requirements.lock"),
    "--executable", $ExecutablePath, "--zip", $ZipPath, "--output", $SbomPath,
    "--source-date-epoch", $SourceDateEpoch
)
if ($ExpectedTag) {
    $SbomArguments += @("--expected-tag", $ExpectedTag)
}
Invoke-Native $Python "CycloneDX SBOM generation" $SbomArguments
$ChecksumsPath = Join-Path $RepoRoot ("dist\{0}" -f $Metadata.checksums_name)
Invoke-Native $Python "release checksum generation" @(
    (Join-Path $PSScriptRoot "generate_checksums.py"), "--output", $ChecksumsPath, $ZipPath, $SbomPath
)
Invoke-Native $Python "release bundle audit" $AuditArguments

Write-Host "Release bundle complete:"
Write-Host "  $ZipPath"
Write-Host "  $SbomPath"
Write-Host "  $ChecksumsPath"
