param()

$ErrorActionPreference = "Stop"
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$Python = Join-Path $RepoRoot ".venv\Scripts\python.exe"

if (-not (Test-Path $Python)) {
    throw "Missing .venv. Create it with 'python -m venv .venv' and install dependencies with '.\.venv\Scripts\python.exe -m pip install -e `".[dev]`"'."
}

Set-Location $RepoRoot
& $Python -m aegisvault
