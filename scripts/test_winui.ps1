param([string]$Executable = 'dist/AegisVault/AegisVault.exe', [string]$Theme = 'light', [string]$Language = 'en-US')
$ErrorActionPreference = 'Stop'
$Dotnet = if ($env:AEGISVAULT_DOTNET) { $env:AEGISVAULT_DOTNET } else { (Get-Command dotnet).Source }
& $Dotnet run --project tests/AegisVault.NativeTests -c Release -- $Executable build/native-evidence $Theme $Language
if ($LASTEXITCODE -ne 0) { throw 'Native WinUI interaction tests failed.' }
