param([string]$OutputPath = 'security-reports/nuget-audit.json')
$ErrorActionPreference = 'Stop'
$Dotnet = if ($env:AEGISVAULT_DOTNET) { $env:AEGISVAULT_DOTNET } else { (Get-Command dotnet).Source }
New-Item -ItemType Directory -Force -Path (Split-Path -Parent $OutputPath) | Out-Null
& $Dotnet list src/AegisVault.App/AegisVault.App.csproj package --vulnerable --include-transitive --format json > $OutputPath
if ($LASTEXITCODE -ne 0) { throw 'NuGet advisory scan failed.' }
$Report = Get-Content -Raw -LiteralPath $OutputPath | ConvertFrom-Json
if (-not $Report.projects -or $Report.version -ne 1) { throw 'Invalid NuGet audit report.' }
foreach ($Problem in $Report.problems) {
    if ($Problem.level -eq 'error') { throw 'NuGet audit reported a tool error.' }
}
foreach ($Project in $Report.projects) {
    foreach ($Framework in $Project.frameworks) {
        foreach ($Package in @($Framework.topLevelPackages) + @($Framework.transitivePackages)) {
            if ($Package.vulnerabilities) { throw "NuGet advisory requires review: $($Package.id)" }
        }
    }
}
Write-Host 'NuGet advisory scan passed; no reported vulnerable dependencies.'
