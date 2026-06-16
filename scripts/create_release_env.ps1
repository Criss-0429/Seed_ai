param(
    [string]$Target = ".release-venv"
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$targetPath = Join-Path $root $Target

uv venv --clear --python 3.14 $targetPath
uv pip install --python (Join-Path $targetPath "Scripts\python.exe") `
    -r (Join-Path $root "requirements-release.txt")

Write-Output "Clean release environment ready: $targetPath"
