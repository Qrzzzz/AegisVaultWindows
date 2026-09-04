param(
    [Parameter(Mandatory = $true)]
    [string]$Executable,
    [ValidateRange(5, 120)]
    [int]$TimeoutSeconds = 30
)

$ErrorActionPreference = "Stop"
$ExecutablePath = (Resolve-Path -LiteralPath $Executable).Path
$SystemTemp = [IO.Path]::GetFullPath([IO.Path]::GetTempPath())
$SmokeRoot = [IO.Path]::GetFullPath((Join-Path $SystemTemp ("aegisvault-smoke-{0}" -f [Guid]::NewGuid().ToString("N"))))
if (-not $SmokeRoot.StartsWith($SystemTemp, [StringComparison]::OrdinalIgnoreCase)) {
    throw "Refusing to create smoke directory outside the system temp root: $SmokeRoot"
}
[IO.Directory]::CreateDirectory($SmokeRoot) | Out-Null

$SavedEnvironment = @{}
foreach ($Name in @("AEGISVAULT_HEADLESS_SMOKE", "QT_QPA_PLATFORM", "APPDATA", "LOCALAPPDATA", "PATH")) {
    $SavedEnvironment[$Name] = [Environment]::GetEnvironmentVariable($Name, "Process")
}
$CleanRuntimePath = @(
    (Join-Path $env:SystemRoot "System32"),
    $env:SystemRoot,
    (Join-Path $env:SystemRoot "System32\Wbem")
) | Where-Object { $_ -and (Test-Path -LiteralPath $_ -PathType Container) } | Select-Object -Unique
$StdoutPath = Join-Path $SmokeRoot "stdout.log"
$StderrPath = Join-Path $SmokeRoot "stderr.log"
$Failure = $null

try {
    $env:AEGISVAULT_HEADLESS_SMOKE = "1"
    $env:QT_QPA_PLATFORM = "offscreen"
    $env:APPDATA = $SmokeRoot
    $env:LOCALAPPDATA = $SmokeRoot
    $env:PATH = $CleanRuntimePath -join [IO.Path]::PathSeparator
    $Process = Start-Process -FilePath $ExecutablePath -WorkingDirectory $SmokeRoot -PassThru -RedirectStandardOutput $StdoutPath -RedirectStandardError $StderrPath
    if (-not $Process.WaitForExit($TimeoutSeconds * 1000)) {
        $Process.Kill($true)
        $Process.WaitForExit()
        $Failure = "Packaged smoke timed out after $TimeoutSeconds seconds."
    } elseif ($Process.ExitCode -ne 0) {
        $Failure = "Packaged smoke failed with exit code $($Process.ExitCode)."
    }
    if ($Failure) {
        $Diagnostic = @(
            Get-Content -LiteralPath $StdoutPath -Tail 80 -ErrorAction SilentlyContinue
            Get-Content -LiteralPath $StderrPath -Tail 120 -ErrorAction SilentlyContinue
        ) -join "`n"
        if (-not [string]::IsNullOrWhiteSpace($Diagnostic)) {
            $Failure = "$Failure`nPackaged process output:`n$Diagnostic"
        }
    }
} finally {
    foreach ($Name in $SavedEnvironment.Keys) {
        [Environment]::SetEnvironmentVariable($Name, $SavedEnvironment[$Name], "Process")
    }
    Remove-Item -LiteralPath $SmokeRoot -Recurse -Force -ErrorAction SilentlyContinue
}

if ($Failure) {
    throw $Failure
}

Write-Host "Packaged headless smoke passed: $ExecutablePath"
