param(
    [switch]$Build,
    [switch]$Zip,
    [switch]$InstallDependencies,
    [switch]$RequireClean,
    [string]$ExpectedCommit,
    [string]$ExpectedTag,
    [string]$DefaultBranch,
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

if ($env:VIRTUAL_ENV) {
    $Python = (Get-Command python -ErrorAction Stop).Source
} elseif (Test-Path (Join-Path $RepoRoot ".venv\Scripts\python.exe")) {
    $Python = Join-Path $RepoRoot ".venv\Scripts\python.exe"
} else {
    throw "No virtual environment found. Create one with: python -m venv .venv"
}

if ($InstallDependencies) {
    & (Join-Path $PSScriptRoot "install_locked_dependencies.ps1") -Python $Python
}

$MetadataArguments = @((Join-Path $PSScriptRoot "release_metadata.py"))
if ($ExpectedTag) {
    $MetadataArguments += @("--expected-tag", $ExpectedTag)
}
Invoke-Native $Python "release metadata validation" $MetadataArguments

if ($ExpectedTag) {
    if ([string]::IsNullOrWhiteSpace($DefaultBranch)) {
        throw "DefaultBranch is required when validating a tagged release."
    }
    $RefArguments = @(
        (Join-Path $PSScriptRoot "verify_release_ref.py"), "--expected-tag", $ExpectedTag,
        "--default-branch", $DefaultBranch
    )
    if ($ExpectedCommit) {
        $RefArguments += @("--expected-commit", $ExpectedCommit)
    }
    if ($RequireClean) {
        $RefArguments += "--require-clean"
    }
    Invoke-Native $Python "release ref validation" $RefArguments
}

$PreviousUtf8 = $env:PYTHONUTF8
$PreviousIoEncoding = $env:PYTHONIOENCODING
$PreviousQtPlatform = $env:QT_QPA_PLATFORM
try {
    $env:PYTHONUTF8 = "1"
    $env:PYTHONIOENCODING = "utf-8"
    $env:QT_QPA_PLATFORM = "offscreen"
    Write-Host "== Compile =="
    Invoke-Native $Python "compileall" @("-m", "compileall", "-q", "src", "tests", "scripts")
    Write-Host "== Ruff =="
    Invoke-Native $Python "ruff" @("-m", "ruff", "check", ".")
    Write-Host "== Mypy =="
    Invoke-Native $Python "mypy" @("-m", "mypy", "src")
    Write-Host "== Pytest and coverage =="
    Invoke-Native $Python "pytest" @(
        "-m", "pytest", "-vv", "--cov=aegisvault", "--cov-report=term-missing", "--cov-report=xml:coverage.xml",
        "--cov-fail-under=70"
    )

    Write-Host "== Source headless smoke =="
    $SystemTemp = [IO.Path]::GetFullPath([IO.Path]::GetTempPath())
    $SmokeRoot = [IO.Path]::GetFullPath((Join-Path $SystemTemp ("aegisvault-source-smoke-{0}" -f [Guid]::NewGuid().ToString("N"))))
    if (-not $SmokeRoot.StartsWith($SystemTemp, [StringComparison]::OrdinalIgnoreCase)) {
        throw "Refusing to create source smoke directory outside the system temp root."
    }
    [IO.Directory]::CreateDirectory($SmokeRoot) | Out-Null
    $PreviousAppData = $env:APPDATA
    $PreviousLocalAppData = $env:LOCALAPPDATA
    $PreviousSmoke = $env:AEGISVAULT_HEADLESS_SMOKE
    try {
        $env:APPDATA = $SmokeRoot
        $env:LOCALAPPDATA = $SmokeRoot
        $env:AEGISVAULT_HEADLESS_SMOKE = "1"
        Invoke-Native $Python "headless smoke" @("-m", "aegisvault")
    } finally {
        $env:APPDATA = $PreviousAppData
        $env:LOCALAPPDATA = $PreviousLocalAppData
        $env:AEGISVAULT_HEADLESS_SMOKE = $PreviousSmoke
        Remove-Item -LiteralPath $SmokeRoot -Recurse -Force -ErrorAction SilentlyContinue
    }
} finally {
    $env:PYTHONUTF8 = $PreviousUtf8
    $env:PYTHONIOENCODING = $PreviousIoEncoding
    $env:QT_QPA_PLATFORM = $PreviousQtPlatform
}

if ($Build) {
    Write-Host "== Windows build =="
    $BuildArguments = @{ Clean = $true; SigningMode = $SigningMode }
    if ($Zip) { $BuildArguments["Zip"] = $true }
    if ($RequireClean) { $BuildArguments["RequireClean"] = $true }
    if ($ExpectedCommit) { $BuildArguments["ExpectedCommit"] = $ExpectedCommit }
    if ($ExpectedTag) { $BuildArguments["ExpectedTag"] = $ExpectedTag }
    & (Join-Path $PSScriptRoot "build_windows.ps1") @BuildArguments
}

Write-Host "Release verification passed."
