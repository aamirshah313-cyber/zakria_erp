$ErrorActionPreference = 'Stop'
$taskRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $taskRoot
if (-not (Test-Path "$taskRoot\apps\client\build\web\index.html")) {
    throw 'Build the browser preview first: cd apps/client; flutter build web --no-wasm-dry-run'
}
& "$taskRoot\.venv\Scripts\python.exe" -m http.server 5173 --bind 127.0.0.1 --directory "$taskRoot\apps\client\build\web"
