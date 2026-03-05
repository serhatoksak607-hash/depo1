param(
    [string]$SourceDir,
    [string]$OutputDir = "exports"
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$pythonExe = Get-ChildItem -Path (Join-Path $env:LocalAppData "Programs\Python") -Recurse -Filter python.exe -ErrorAction SilentlyContinue |
    Where-Object { $_.FullName -notmatch "\\venv\\" } |
    Sort-Object FullName -Descending |
    Select-Object -First 1 -ExpandProperty FullName

if (-not $pythonExe -or -not (Test-Path $pythonExe)) {
    throw "Python bulunamadi. Lutfen Python 3.12 kurulu oldugunu kontrol et."
}

& $pythonExe -m pip install pypdf | Out-Null

$appPath = Join-Path $repoRoot "tools\ticket_scan_app.py"
if ($SourceDir) {
    & $pythonExe $appPath --source-dir $SourceDir --output-dir $OutputDir
}
else {
    & $pythonExe $appPath --picker --output-dir $OutputDir
}

