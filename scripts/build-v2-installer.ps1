param(
    [string]$Package,
    [string]$AppVersion = '2.1.0',
    [string]$Iscc = (Join-Path $env:LOCALAPPDATA 'Programs\Inno Setup 6\ISCC.exe')
)
# Builds the Windows installer from a package made by package-v2-windows.ps1.
# The developer data-directory.txt is excluded, so installed copies use the
# shared C:\ProgramData\ZakariaERP folder and first-run administrator setup.
$ErrorActionPreference = 'Stop'
$taskRoot = Split-Path -Parent $PSScriptRoot
$taskArtifacts = Join-Path $taskRoot 'artifacts\windows-v2'
if (-not (Test-Path -LiteralPath $Iscc)) { throw "Inno Setup compiler not found at $Iscc. Install JRSoftware.InnoSetup or pass -Iscc." }
if (-not $Package) {
    $latest = Get-ChildItem -LiteralPath $taskArtifacts -Directory -Filter 'ZakariaERP-V2-*' | Sort-Object Name | Select-Object -Last 1
    if (-not $latest) { throw 'No package found. Run scripts\package-v2-windows.ps1 first.' }
    $Package = $latest.FullName
}
foreach ($required in @('ZakariaERP.exe', 'flutter_windows.dll', 'data', 'backend\zakaria_service.exe')) {
    if (-not (Test-Path -LiteralPath (Join-Path $Package $required))) { throw "Package is incomplete: $required missing in $Package" }
}
$taskStage = Join-Path $taskRoot 'artifacts\installer-stage'
if (Test-Path -LiteralPath $taskStage) { Remove-Item -LiteralPath $taskStage -Recurse -Force }
New-Item -ItemType Directory -Path $taskStage | Out-Null
Copy-Item -Path (Join-Path $Package '*') -Destination $taskStage -Recurse -Exclude 'data-directory.txt', 'READ-ME.txt'
if (Test-Path -LiteralPath (Join-Path $taskStage 'data-directory.txt')) { throw 'Staging must not contain data-directory.txt.' }
$taskPrivateFiles = Get-ChildItem -LiteralPath $taskStage -Recurse -File | Where-Object { $_.Name -match '(?i)(\.sqlite3?$|^service-secret\.txt$|^\.env($|\.))' }
if ($taskPrivateFiles) { throw 'Unexpected private database/configuration file in staging; review before building.' }
$taskOutput = Join-Path $taskRoot 'artifacts\installer'
New-Item -ItemType Directory -Force -Path $taskOutput | Out-Null
& $Iscc "/DSourceDir=$taskStage" "/DAppVersion=$AppVersion" "/DOutputDir=$taskOutput" (Join-Path $taskRoot 'installer\ZakariaERP.iss')
if ($LASTEXITCODE -ne 0) { throw 'Installer compilation failed.' }
$taskSetup = Join-Path $taskOutput "ZakariaERP-Setup-$AppVersion.exe"
Write-Output "Installer: $taskSetup ($((Get-Item -LiteralPath $taskSetup).Length) bytes)"
Write-Output "Built from: $Package"
Write-Output 'Unsigned: Windows SmartScreen will warn until the installer is code-signed.'
