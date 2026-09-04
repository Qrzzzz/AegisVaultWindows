param([int]$TimeoutSeconds = 120)
$ErrorActionPreference = 'Stop'
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$Dotnet = if ($env:AEGISVAULT_DOTNET) { $env:AEGISVAULT_DOTNET } else { (Get-Command dotnet -ErrorAction Stop).Source }
$Python = if ($env:VIRTUAL_ENV) { Join-Path $env:VIRTUAL_ENV 'Scripts\python.exe' } else { Join-Path $RepoRoot '.venv\Scripts\python.exe' }
if (-not (Test-Path -LiteralPath $Python)) { throw "Python environment is unavailable: $Python" }
$OutputRoot = Join-Path $RepoRoot 'build\ipc-lifecycle'
$ClientOutput = Join-Path $OutputRoot 'client'
$BackendOutput = Join-Path $ClientOutput 'backend'
New-Item -ItemType Directory -Force -Path $ClientOutput,$BackendOutput | Out-Null

& $Dotnet build (Join-Path $RepoRoot 'tests\AegisVault.IpcTests') -c Release -warnaserror -o $ClientOutput
if ($LASTEXITCODE -ne 0) { throw 'IPC lifecycle client build failed.' }
& $Dotnet build (Join-Path $RepoRoot 'tests\AegisVault.IpcStub') -c Release -warnaserror -o $BackendOutput
if ($LASTEXITCODE -ne 0) { throw 'IPC lifecycle stub build failed.' }

$Stdout = Join-Path $OutputRoot 'results.jsonl'
$Stderr = Join-Path $OutputRoot 'stderr.log'
$PreviousPython = $env:AEGISVAULT_TEST_PYTHON
$PreviousSource = $env:AEGISVAULT_TEST_SOURCE
try {
    $env:AEGISVAULT_TEST_PYTHON = $Python
    $env:AEGISVAULT_TEST_SOURCE = Join-Path $RepoRoot 'src'
    $Runner = Start-Process -FilePath (Join-Path $ClientOutput 'AegisVault.IpcTests.exe') -WindowStyle Hidden `
        -PassThru -RedirectStandardOutput $Stdout -RedirectStandardError $Stderr
    if (-not $Runner.WaitForExit($TimeoutSeconds * 1000)) {
        $Runner.Kill($true)
        throw "IPC lifecycle harness exceeded its $TimeoutSeconds-second external deadline."
    }
    $Runner.Refresh()
    Get-Content -LiteralPath $Stdout
    if ($Runner.ExitCode -ne 0) {
        Get-Content -LiteralPath $Stderr | Select-Object -First 80
        throw "IPC lifecycle harness failed with exit code $($Runner.ExitCode)."
    }
} finally {
    $env:AEGISVAULT_TEST_PYTHON = $PreviousPython
    $env:AEGISVAULT_TEST_SOURCE = $PreviousSource
}
