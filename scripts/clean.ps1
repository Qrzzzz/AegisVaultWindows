param()

$ErrorActionPreference = "Stop"
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path

Remove-Item -Recurse -Force `
    (Join-Path $RepoRoot "build"), `
    (Join-Path $RepoRoot "dist"), `
    (Join-Path $RepoRoot ".mypy_cache"), `
    (Join-Path $RepoRoot ".ruff_cache"), `
    (Join-Path $RepoRoot ".pytest_cache") `
    -ErrorAction SilentlyContinue

Get-ChildItem -Path $RepoRoot -Recurse -Directory -Filter "__pycache__" -ErrorAction SilentlyContinue |
    Remove-Item -Recurse -Force -ErrorAction SilentlyContinue

Write-Host "Cleaned generated build and test cache files."
