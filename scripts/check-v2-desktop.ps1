param([string]$FlutterSdk = 'C:\Users\DELL\tools\flutter')
$ErrorActionPreference = 'Stop'
$taskRoot = Split-Path -Parent $PSScriptRoot
$taskVswhere = Join-Path ${env:ProgramFiles(x86)} 'Microsoft Visual Studio\Installer\vswhere.exe'
$taskCompiler = ''
if (Test-Path -LiteralPath $taskVswhere) {
    $taskCompiler = & $taskVswhere -latest -products '*' -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath
}
$taskDeveloperMode = $false
try {
    $taskDeveloperMode = (Get-ItemPropertyValue -Path 'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\AppModelUnlock' -Name AllowDevelopmentWithoutDevLicense -ErrorAction Stop) -eq 1
} catch { }
[pscustomobject]@{
    PythonEnvironment = Test-Path -LiteralPath (Join-Path $taskRoot '.venv\Scripts\python.exe')
    FlutterSDK = Test-Path -LiteralPath (Join-Path $FlutterSdk 'bin\cache\flutter_tools.snapshot')
    WindowsCppToolchain = [bool]$taskCompiler
    DeveloperMode = $taskDeveloperMode
    V2Database = Test-Path -LiteralPath (Join-Path $taskRoot 'storage\v2-desktop\register.sqlite3')
    NativeRunnerSource = Test-Path -LiteralPath (Join-Path $taskRoot 'apps\client\windows\runner\main.cpp')
} | Format-List
if (-not $taskCompiler) { Write-Output 'Required for EXE builds: Visual Studio Desktop development with C++, including MSVC, CMake tools and Windows SDK.' }
if (-not $taskDeveloperMode) { Write-Output 'Enable Windows Developer Mode for Flutter plugin symbolic-link support (or provide equivalent permitted symlink capability).' }
