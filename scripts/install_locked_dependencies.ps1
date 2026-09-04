param(
    [string]$Python
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

if ([string]::IsNullOrWhiteSpace($Python)) {
    if ($env:VIRTUAL_ENV) {
        $Python = (Get-Command python -ErrorAction Stop).Source
    } elseif (Test-Path (Join-Path $RepoRoot ".venv\Scripts\python.exe")) {
        $Python = Join-Path $RepoRoot ".venv\Scripts\python.exe"
    } else {
        throw "No virtual environment found. Create one with 'python -m venv .venv'."
    }
}

$LockPath = Join-Path $RepoRoot "requirements-dev.lock"
if (-not (Test-Path -LiteralPath $LockPath -PathType Leaf)) {
    throw "Missing hashed dependency lock: $LockPath"
}

$PreviousUtf8 = $env:PYTHONUTF8
$PreviousIoEncoding = $env:PYTHONIOENCODING
try {
    $env:PYTHONUTF8 = "1"
    $env:PYTHONIOENCODING = "utf-8"
    Invoke-Native $Python "hash-locked dependency install" @(
        "-m", "pip", "install", "--quiet", "--disable-pip-version-check", "--require-hashes", "--only-binary=:all:", "-r", $LockPath
    )
    Invoke-Native $Python "editable source install" @(
        "-m", "pip", "install", "--quiet", "--disable-pip-version-check", "--no-deps", "--no-build-isolation", "-e", "."
    )
    Invoke-Native $Python "installed dependency consistency" @("-m", "pip", "check")
} finally {
    $env:PYTHONUTF8 = $PreviousUtf8
    $env:PYTHONIOENCODING = $PreviousIoEncoding
}

Write-Host "Installed the hash-locked development and packaging environment."
