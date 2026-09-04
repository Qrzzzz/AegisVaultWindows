param(
    [Parameter(Mandatory = $true)]
    [string]$OutputPath,
    [string]$Python
)

$ErrorActionPreference = "Stop"
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
if ([string]::IsNullOrWhiteSpace($Python)) {
    if ($env:VIRTUAL_ENV) {
        $Python = (Get-Command python -ErrorAction Stop).Source
    } elseif (Test-Path (Join-Path $RepoRoot ".venv\Scripts\python.exe")) {
        $Python = Join-Path $RepoRoot ".venv\Scripts\python.exe"
    } else {
        throw "No virtual environment found for pip-audit."
    }
}
$ResolvedOutput = [IO.Path]::GetFullPath((Join-Path $RepoRoot $OutputPath))
[IO.Directory]::CreateDirectory((Split-Path -Parent $ResolvedOutput)) | Out-Null

$PreviousUtf8 = $env:PYTHONUTF8
$PreviousIoEncoding = $env:PYTHONIOENCODING
try {
    $env:PYTHONUTF8 = "1"
    $env:PYTHONIOENCODING = "utf-8"
    & $Python -m pip_audit -r (Join-Path $RepoRoot "requirements.lock") --format json --output $ResolvedOutput --progress-spinner off
    $AuditStatus = $LASTEXITCODE
} finally {
    $env:PYTHONUTF8 = $PreviousUtf8
    $env:PYTHONIOENCODING = $PreviousIoEncoding
}

if (-not (Test-Path -LiteralPath $ResolvedOutput -PathType Leaf)) {
    $Fallback = [ordered]@{
        schema = "aegisvault-pip-audit-wrapper-v1"
        tool_error = $true
        exit_code = $AuditStatus
    } | ConvertTo-Json
    [IO.File]::WriteAllText($ResolvedOutput, $Fallback + [Environment]::NewLine, [Text.UTF8Encoding]::new($false))
}
Write-Host "pip-audit report: $ResolvedOutput"
exit $AuditStatus
