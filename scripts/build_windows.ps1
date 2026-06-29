param(
    [switch]$Clean,
    [switch]$Zip
)

$ErrorActionPreference = "Stop"

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $RepoRoot

if (-not (Test-Path (Join-Path $RepoRoot "pyproject.toml"))) {
    throw "build_windows.ps1 must be run from a valid AegisVault repository checkout."
}

$SpecPath = Join-Path $RepoRoot "scripts\aegisvault.spec"
$IconPath = Join-Path $RepoRoot "src\aegisvault\resources\app_icon.ico"
$LocalePath = Join-Path $RepoRoot "src\aegisvault\i18n\locales"

if (-not (Test-Path $SpecPath)) {
    throw "Missing PyInstaller spec: $SpecPath"
}
if (-not (Test-Path $IconPath)) {
    throw "Missing application icon: $IconPath"
}
if (-not (Test-Path $LocalePath)) {
    throw "Missing locale directory: $LocalePath"
}
foreach ($LocaleName in @("en-US.json", "zh-CN.json")) {
    $LocaleFile = Join-Path $LocalePath $LocaleName
    if (-not (Test-Path $LocaleFile)) {
        throw "Missing locale file: $LocaleFile"
    }
}

if ($env:VIRTUAL_ENV) {
    $Python = (Get-Command python -ErrorAction Stop).Source
} elseif (Test-Path (Join-Path $RepoRoot ".venv\Scripts\python.exe")) {
    $Python = Join-Path $RepoRoot ".venv\Scripts\python.exe"
} else {
    throw "No virtual environment found. Create one with 'python -m venv .venv' and install with 'python -m pip install -e `".[dev]`"'."
}

if ($Clean) {
    Remove-Item -Recurse -Force (Join-Path $RepoRoot "build"), (Join-Path $RepoRoot "dist") -ErrorAction SilentlyContinue
}

& $Python -m pip install --upgrade pip
& $Python -m pip install -e ".[dev]"

$BuildLog = New-TemporaryFile
$PreviousErrorActionPreference = $ErrorActionPreference
try {
    $ErrorActionPreference = "Continue"
    & $Python -m PyInstaller --noconfirm $SpecPath *> $BuildLog
    $BuildStatus = $LASTEXITCODE
    $ErrorActionPreference = $PreviousErrorActionPreference
    if ($BuildStatus -ne 0) {
        Write-Host "PyInstaller failed. Last log lines:"
        Get-Content -LiteralPath $BuildLog -Tail 120
        exit $BuildStatus
    }
} finally {
    $ErrorActionPreference = $PreviousErrorActionPreference
    Remove-Item -LiteralPath $BuildLog -Force -ErrorAction SilentlyContinue
}

$OutputPath = Join-Path $RepoRoot "dist\AegisVault.exe"
if (-not (Test-Path $OutputPath)) {
    throw "Build completed but executable was not found at $OutputPath"
}

Write-Host "Build complete: $OutputPath"

if ($Zip) {
    $Version = (& $Python -c "from aegisvault.version import RELEASE_TAG; print(RELEASE_TAG)").Trim()
    if (-not $Version.StartsWith("v")) {
        throw "Release tag must start with v, got: $Version"
    }
    $ZipName = "AegisVault-$Version-win64.zip"
    $ZipPath = Join-Path $RepoRoot "dist\$ZipName"
    if (Test-Path $ZipPath) {
        Remove-Item -LiteralPath $ZipPath -Force
    }
    Compress-Archive -LiteralPath $OutputPath -DestinationPath $ZipPath -Force
    if (-not (Test-Path $ZipPath)) {
        throw "ZIP artifact was not created: $ZipPath"
    }
    Write-Host "ZIP complete: $ZipPath"
}
