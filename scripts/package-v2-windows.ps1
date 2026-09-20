param([switch]$BackendOnly, [switch]$UseExistingBackend, [string]$FlutterSdk = 'C:\Users\DELL\tools\flutter')
$ErrorActionPreference = 'Stop'
$taskRoot = Split-Path -Parent $PSScriptRoot
$taskPython = Join-Path $taskRoot '.venv\Scripts\python.exe'
$taskArtifacts = Join-Path $taskRoot 'artifacts\windows-v2'
$taskData = Join-Path $taskRoot 'storage\v2-desktop'
$taskDart = Join-Path $FlutterSdk 'bin\cache\dart-sdk\bin\dart.exe'
$taskFlutter = Join-Path $FlutterSdk 'bin\cache\flutter_tools.snapshot'
Set-Location -LiteralPath $taskRoot
New-Item -ItemType Directory -Force -Path $taskArtifacts | Out-Null
$env:DJANGO_SETTINGS_MODULE = 'config.desktop'
$env:ERP_DESKTOP_DATA_DIR = $taskData
if (-not $UseExistingBackend) {
    & $taskPython -m PyInstaller --noconfirm --onedir --console --name zakaria_service --paths backend --distpath "$taskArtifacts\service" --workpath "$taskArtifacts\work" --specpath "$taskArtifacts" --collect-submodules core --collect-submodules config --collect-all rest_framework --collect-all corsheaders --collect-all reportlab --collect-all openpyxl --collect-all PIL --hidden-import django.db.backends.sqlite3 --exclude-module numpy --add-data "${taskRoot}/backend/resources:resources" backend/desktop_service.py
    if ($LASTEXITCODE -ne 0) { throw 'Bundled backend build failed.' }
}
if (-not (Test-Path -LiteralPath "$taskArtifacts\service\zakaria_service\zakaria_service.exe")) { throw 'The bundled backend executable is missing.' }
if ($BackendOnly) { Write-Output "Backend package: $taskArtifacts\service\zakaria_service"; exit 0 }
Set-Location -LiteralPath (Join-Path $taskRoot 'apps\client')
& $taskDart $taskFlutter build windows --release --no-pub --build-name=2.1.0 --build-number=12 --dart-define=V2_DESKTOP=true --dart-define=API_URL=http://127.0.0.1:8765/api
if ($LASTEXITCODE -ne 0) { throw 'Windows client build failed. Check C++ toolchain and symbolic-link privileges.' }
$taskRelease = Join-Path $taskRoot 'apps\client\build\windows\x64\runner\Release'
$taskPackage = Join-Path $taskArtifacts ('ZakariaERP-V2-' + (Get-Date -Format 'yyyyMMdd-HHmmss'))
if (Test-Path -LiteralPath $taskPackage) { throw 'A package with this timestamp already exists.' }
New-Item -ItemType Directory -Path $taskPackage | Out-Null
Copy-Item -Path "$taskRelease\*" -Destination $taskPackage -Recurse
Copy-Item -LiteralPath "$taskArtifacts\service\zakaria_service" -Destination "$taskPackage\backend" -Recurse
[IO.File]::WriteAllText((Join-Path $taskPackage 'data-directory.txt'), $taskData, [Text.UTF8Encoding]::new($false))
$taskClient = Join-Path $taskPackage 'zakaria_erp.exe'
if (-not (Test-Path -LiteralPath $taskClient)) { throw 'Expected native client executable is missing.' }
Rename-Item -LiteralPath $taskClient -NewName 'ZakariaERP.exe'
@'
Muhammad Zakaria and Sons - V2 Windows acceptance package

Run ZakariaERP.exe. Keep the entire folder together; the EXE needs its DLLs,
Flutter data and bundled backend. No browser or separate terminal is required.
The backend starts privately on 127.0.0.1:8765 and stops with this application.

This test package uses the existing isolated V2 database folder named in
data-directory.txt. It contains no company database, password or secret file.
Use your existing registered V2 account. Do not point it at the pilot database.

The package is unsigned and prepared for acceptance on this computer.
Installing on another computer requires a reviewed V2 data transfer/setup;
a general-purpose installer and first-run setup are separate deliverables.
Back up the complete V2 data directory before moving it or installing upgrades.
'@ | Set-Content -LiteralPath (Join-Path $taskPackage 'READ-ME.txt') -Encoding utf8
$taskPrivateFiles = Get-ChildItem -LiteralPath $taskPackage -Recurse -File | Where-Object { $_.Name -match '(?i)(\.sqlite3?$|^service-secret\.txt$|^\.env($|\.))' }
if ($taskPrivateFiles) { throw 'Unexpected private database/configuration file in package; review before distribution.' }
Compress-Archive -LiteralPath $taskPackage -DestinationPath "$taskPackage.zip"
Write-Output "Native EXE: $taskPackage\ZakariaERP.exe"
Write-Output "Complete package: $taskPackage.zip"
