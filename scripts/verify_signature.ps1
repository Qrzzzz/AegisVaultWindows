param([Parameter(Mandatory=$true)][string]$Executable)
$ErrorActionPreference = 'Stop'
$Signature = Get-AuthenticodeSignature -LiteralPath $Executable
if ($Signature.Status -ne 'Valid') { throw "Invalid Authenticode signature: $($Signature.Status)" }
Write-Host 'Authenticode signature valid.'
