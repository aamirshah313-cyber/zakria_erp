$ErrorActionPreference = 'Stop'
$taskRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $taskRoot
& "$taskRoot\.venv\Scripts\python.exe" "$taskRoot\backend\manage.py" migrate
if ($LASTEXITCODE -ne 0) { throw 'Database migration failed.' }
& "$taskRoot\.venv\Scripts\python.exe" "$taskRoot\backend\manage.py" bootstrap
