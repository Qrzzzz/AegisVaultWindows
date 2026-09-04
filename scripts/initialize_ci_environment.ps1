param(
    [string]$EnvironmentPath = ".venv",
    [string]$BasePython,
    [switch]$ExportGitHubEnvironment
)

$ErrorActionPreference = "Stop"
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$EnvironmentRoot = [IO.Path]::GetFullPath($EnvironmentPath, $RepoRoot)
$RepoPrefix = $RepoRoot.TrimEnd([IO.Path]::DirectorySeparatorChar) + [IO.Path]::DirectorySeparatorChar
if (-not $EnvironmentRoot.StartsWith($RepoPrefix, [StringComparison]::OrdinalIgnoreCase)) {
    throw "The isolated environment must be inside the checkout: $EnvironmentRoot"
}
if (Test-Path -LiteralPath $EnvironmentRoot) {
    throw "Refusing to reuse or replace an existing environment: $EnvironmentRoot"
}
if ($ExportGitHubEnvironment) {
    foreach ($File in @($env:GITHUB_ENV, $env:GITHUB_PATH)) {
        if ([string]::IsNullOrWhiteSpace($File) -or -not (Test-Path -LiteralPath $File -PathType Leaf)) {
            throw "GitHub environment export requires existing GITHUB_ENV and GITHUB_PATH files."
        }
    }
}
if ([string]::IsNullOrWhiteSpace($BasePython)) {
    # Application lookup can return every PATH match; preserve setup-python/venv priority as one path.
    $BasePython = (Get-Command python -CommandType Application -ErrorAction Stop | Select-Object -First 1).Source
}
$BasePython = (Resolve-Path -LiteralPath $BasePython).Path
& $BasePython -m venv $EnvironmentRoot
if ($LASTEXITCODE -ne 0) {
    throw "Creating the isolated Python environment failed with exit code $LASTEXITCODE."
}

$ScriptsDirectory = Join-Path $EnvironmentRoot "Scripts"
$EnvironmentPython = Join-Path $ScriptsDirectory "python.exe"
if (-not (Test-Path -LiteralPath $EnvironmentPython -PathType Leaf)) {
    throw "The new environment has no Windows Python interpreter: $EnvironmentPython"
}
$ProbeJson = (& $EnvironmentPython -c "import json, sys; print(json.dumps({'prefix': sys.prefix, 'base_prefix': sys.base_prefix}))") -join "`n"
if ($LASTEXITCODE -ne 0) {
    throw "The new environment interpreter failed its isolation probe."
}
$Probe = $ProbeJson | ConvertFrom-Json
if ([IO.Path]::GetFullPath($Probe.prefix) -ne $EnvironmentRoot -or $Probe.prefix -eq $Probe.base_prefix) {
    throw "The new Python interpreter is not isolated at the requested path: $EnvironmentRoot"
}

$env:VIRTUAL_ENV = $EnvironmentRoot
$env:PATH = $ScriptsDirectory + [IO.Path]::PathSeparator + $env:PATH
$ResolvedPython = (Get-Command python -ErrorAction Stop).Source
if ([IO.Path]::GetFullPath($ResolvedPython) -ne $EnvironmentPython) {
    throw "The python command did not resolve to the new isolated environment."
}
if ($ExportGitHubEnvironment) {
    $Utf8 = [Text.UTF8Encoding]::new($false)
    [IO.File]::AppendAllText($env:GITHUB_ENV, "VIRTUAL_ENV=$EnvironmentRoot`n", $Utf8)
    [IO.File]::AppendAllText($env:GITHUB_PATH, "$ScriptsDirectory`n", $Utf8)
}
Write-Host "Isolated Python environment ready: $EnvironmentPython"
