param([switch]$CopyPilot)
$ErrorActionPreference = 'Stop'
$taskRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $taskRoot
$taskPython = Join-Path $taskRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $taskPython)) { throw 'Project Python environment is missing.' }
$taskArgs = @('scripts/prepare_v2_desktop.py')
if ($CopyPilot) { $taskArgs += '--copy-pilot' }
& $taskPython @taskArgs
if ($LASTEXITCODE -ne 0) { throw 'Desktop initialization failed.' }
& $taskPython backend/manage.py migrate --noinput --settings=config.desktop
if ($LASTEXITCODE -ne 0) { throw 'Desktop database migration failed.' }
& $taskPython backend/manage.py check --settings=config.desktop
if ($LASTEXITCODE -ne 0) { throw 'Desktop configuration check failed.' }
