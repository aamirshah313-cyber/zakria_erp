$ErrorActionPreference = 'Stop'
$taskRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath (Join-Path $taskRoot 'backend')
$env:DJANGO_SETTINGS_MODULE = 'config.desktop'
$taskPython = Join-Path $taskRoot '.venv\Scripts\python.exe'
& $taskPython -m waitress --listen=127.0.0.1:8765 config.wsgi:application
if ($LASTEXITCODE -ne 0) { throw 'Desktop service could not start. Check desktop dependencies and port 8765.' }
