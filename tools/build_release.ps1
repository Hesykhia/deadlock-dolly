# Build a local Deadlock Dolly Windows release. Nothing is uploaded or published.
#
# Usage (from anywhere):
#   powershell -NoProfile -ExecutionPolicy Bypass -File tools\build_release.ps1
#
# It runs tools\build_windows.py with the pinned build virtualenv, then prints
# the dist artifact paths, byte sizes and SHA-256 hashes for you to publish.

[CmdletBinding()]
param(
    [string]$RepoRoot,
    [string]$BuildPython
)

$ErrorActionPreference = "Stop"

if (-not $RepoRoot) {
    $RepoRoot = Split-Path -Parent $PSScriptRoot
}
$RepoRoot = (Resolve-Path -LiteralPath $RepoRoot).Path

if (-not $BuildPython) {
    $BuildPython = Join-Path $RepoRoot "build\venv-build\Scripts\python.exe"
}

if (-not (Test-Path -LiteralPath $BuildPython)) {
    throw "Build interpreter not found: $BuildPython`nCreate it with Python 3.12 x64 and 'pip install -r requirements-build.txt'."
}

$buildScript = Join-Path $RepoRoot "tools\build_windows.py"
if (-not (Test-Path -LiteralPath $buildScript)) {
    throw "Build entry point not found: $buildScript"
}

$version = (& $BuildPython -c "import sys; sys.path.insert(0, r'$RepoRoot'); from dolly import __version__; print(__version__)").Trim()
if (-not $version) {
    throw "Could not read dolly.__version__"
}

& $BuildPython $buildScript
if ($LASTEXITCODE -ne 0) {
    throw "build_windows.py failed with exit code $LASTEXITCODE"
}

$dist = Join-Path $RepoRoot "dist"
Write-Host ""
Write-Host "Artifacts for $version in $dist :"
Get-ChildItem -LiteralPath $dist -Filter "Deadlock_Dolly_${version}_*" |
    Sort-Object Name |
    ForEach-Object {
        $hash = (Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash
        Write-Host ("  {0}" -f $_.FullName)
        Write-Host ("    bytes:  {0}" -f $_.Length)
        Write-Host ("    sha256: {0}" -f $hash)
    }
Write-Host ""
Write-Host "Nothing was uploaded or published. Publish these artifacts yourself."
