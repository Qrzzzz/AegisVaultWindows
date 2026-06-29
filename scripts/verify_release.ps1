param(
    [switch]$Build,
    [switch]$Zip
)

$ErrorActionPreference = "Stop"

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $RepoRoot

function Invoke-Native {
    param(
        [Parameter(Mandatory = $true)]
        [string]$FilePath,
        [Parameter(Mandatory = $true)]
        [string]$Description,
        [string[]]$Arguments
    )

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

Write-Host "== Install =="
Invoke-Native $Python "pip upgrade" @("-m", "pip", "install", "--upgrade", "pip")
Invoke-Native $Python "editable development install" @("-m", "pip", "install", "-e", ".[dev]")

Write-Host "== Compile =="
Invoke-Native $Python "compileall" @("-m", "compileall", "src", "tests")

Write-Host "== Ruff =="
Invoke-Native $Python "ruff" @("-m", "ruff", "check", ".")

Write-Host "== Mypy =="
Invoke-Native $Python "mypy" @("-m", "mypy", "src")

Write-Host "== Pytest =="
Invoke-Native $Python "pytest" @("-m", "pytest", "-vv")

Write-Host "== Headless smoke =="
try {
    $env:AEGISVAULT_HEADLESS_SMOKE = "1"
    Invoke-Native $Python "headless smoke" @("-m", "aegisvault")
} finally {
    Remove-Item Env:\AEGISVAULT_HEADLESS_SMOKE -ErrorAction SilentlyContinue
}

if ($Build) {
    Write-Host "== Build =="
    if ($Zip) {
        .\scripts\build_windows.ps1 -Clean -Zip
        $ZipPath = Join-Path $RepoRoot "dist\AegisVault-v1.0.0-win64.zip"
        if (-not (Test-Path $ZipPath)) {
            throw "Expected release artifact missing: $ZipPath"
        }
    } else {
        .\scripts\build_windows.ps1 -Clean
    }
}

Write-Host "Release verification passed."
