$ErrorActionPreference = 'Stop'
$taskRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $taskRoot
& "$taskRoot\.venv\Scripts\python.exe" "$taskRoot\backend\manage.py" runserver 127.0.0.1:8000
