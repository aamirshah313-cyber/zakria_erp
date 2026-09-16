param([switch]$UseExistingBackend)
$ErrorActionPreference = 'Stop'
$taskRoot = Split-Path -Parent $PSScriptRoot
$taskLog = Join-Path $taskRoot 'storage\v2-desktop\native-build.log'
$taskExitFile = Join-Path $taskRoot 'storage\v2-desktop\native-build-exit.txt'
$taskExit = 1
Start-Transcript -LiteralPath $taskLog -Force
try {
    & (Join-Path $PSScriptRoot 'package-v2-windows.ps1') -UseExistingBackend:$UseExistingBackend
    $taskExit = 0
} catch {
    Write-Output $_
} finally {
    Stop-Transcript
    [IO.File]::WriteAllText($taskExitFile, [string]$taskExit)
}
exit $taskExit
