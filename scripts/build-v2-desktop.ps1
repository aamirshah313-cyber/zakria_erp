param([string]$FlutterSdk = 'C:\Users\DELL\tools\flutter')
$ErrorActionPreference = 'Stop'
$taskRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath (Join-Path $taskRoot 'apps\client')
$taskDart = Join-Path $FlutterSdk 'bin\cache\dart-sdk\bin\dart.exe'
$taskFlutter = Join-Path $FlutterSdk 'bin\cache\flutter_tools.snapshot'
if (-not (Test-Path -LiteralPath $taskDart)) { throw 'Set FlutterSdk to your installed Flutter directory.' }
& $taskDart $taskFlutter build windows --release --dart-define=V2_DESKTOP=true --dart-define=API_URL=http://127.0.0.1:8765/api
if ($LASTEXITCODE -ne 0) { throw 'Desktop build failed; check Visual Studio C++ workload and Developer Mode.' }
Write-Output 'Native client built against the isolated desktop service. This is a developer build, not the final V2 installer or completed V2 feature set.'
