param(
    [Parameter(Mandatory = $true)]
    [string]$Executable,
    [ValidateSet("Optional", "Required")]
    [string]$SigningMode = "Optional"
)

$ErrorActionPreference = "Stop"
$ExecutablePath = (Resolve-Path -LiteralPath $Executable).Path

function Find-SignTool {
    $Command = Get-Command signtool.exe -ErrorAction SilentlyContinue
    if ($Command) {
        return $Command.Source
    }
    $KitsRoot = Join-Path ${env:ProgramFiles(x86)} "Windows Kits\10\bin"
    if (Test-Path -LiteralPath $KitsRoot) {
        $Candidate = Get-ChildItem -LiteralPath $KitsRoot -Directory -ErrorAction SilentlyContinue |
            Sort-Object Name -Descending |
            ForEach-Object { Join-Path $_.FullName "x64\signtool.exe" } |
            Where-Object { Test-Path -LiteralPath $_ -PathType Leaf } |
            Select-Object -First 1
        if ($Candidate) {
            return $Candidate
        }
    }
    return $null
}

$CertificateBase64 = $env:AEGISVAULT_SIGNING_CERTIFICATE_BASE64
$CertificatePassword = $env:AEGISVAULT_SIGNING_CERTIFICATE_PASSWORD
$TimestampUrl = if ($env:AEGISVAULT_TIMESTAMP_URL) { $env:AEGISVAULT_TIMESTAMP_URL } else { "http://timestamp.digicert.com" }

if ([string]::IsNullOrWhiteSpace($CertificateBase64)) {
    $ExistingSignature = Get-AuthenticodeSignature -LiteralPath $ExecutablePath
    if ($ExistingSignature.Status -eq "Valid") {
        Write-Host "SIGNING_STATUS=valid-existing"
        return
    }
    if ($ExistingSignature.Status -ne "NotSigned") {
        throw "Executable has an invalid existing Authenticode state: $($ExistingSignature.Status)"
    }
    if ($SigningMode -eq "Required") {
        throw "Code signing is required, but AEGISVAULT_SIGNING_CERTIFICATE_BASE64 is not configured."
    }
    Write-Warning "SIGNING_STATUS=unsigned-optional (no certificate secret configured)"
    return
}

if ([string]::IsNullOrWhiteSpace($CertificatePassword)) {
    throw "A signing certificate was supplied without AEGISVAULT_SIGNING_CERTIFICATE_PASSWORD."
}
$SignTool = Find-SignTool
if (-not $SignTool) {
    throw "A signing certificate was supplied, but signtool.exe was not found."
}

$PfxPath = Join-Path ([IO.Path]::GetTempPath()) ("aegisvault-signing-{0}.pfx" -f [Guid]::NewGuid().ToString("N"))
try {
    $NormalizedCertificate = $CertificateBase64 -replace "\s", ""
    [IO.File]::WriteAllBytes($PfxPath, [Convert]::FromBase64String($NormalizedCertificate))
    & $SignTool sign /fd SHA256 /td SHA256 /tr $TimestampUrl /f $PfxPath /p $CertificatePassword $ExecutablePath
    if ($LASTEXITCODE -ne 0) {
        throw "signtool failed with exit code $LASTEXITCODE."
    }
} finally {
    Remove-Item -LiteralPath $PfxPath -Force -ErrorAction SilentlyContinue
}

$Signature = Get-AuthenticodeSignature -LiteralPath $ExecutablePath
if ($Signature.Status -ne "Valid") {
    throw "Authenticode verification failed after signing: $($Signature.Status)"
}
Write-Host "SIGNING_STATUS=valid-new"
