param()

$ErrorActionPreference = "Stop"
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$Python = Join-Path $RepoRoot ".venv\Scripts\python.exe"

if (-not (Test-Path $Python)) {
    throw "Missing .venv. Create it with 'python -m venv .venv' and install dependencies with '.\.venv\Scripts\python.exe -m pip install -e `".[dev]`"'."
}

Set-Location $RepoRoot
$Dotnet = if ($env:AEGISVAULT_DOTNET) { $env:AEGISVAULT_DOTNET } else { (Get-Command dotnet -ErrorAction Stop).Source }
$env:AEGISVAULT_PYTHON = $Python
& $Dotnet run --project src/AegisVault.App/AegisVault.App.csproj -c Debug -p:Platform=x64
if ($LASTEXITCODE -ne 0) { throw 'WinUI development launch failed.' }
