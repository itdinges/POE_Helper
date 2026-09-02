param(
    [string]$League = "Runes of Aldur",
    [string]$OutputDir = "data/market"
)

$ErrorActionPreference = "Stop"

# Starter path for the database-fill test: fetch only Currency and Fragments.

$root = Split-Path -Parent $PSScriptRoot
$python = Join-Path $root ".venv\Scripts\python.exe"

if (-not (Test-Path $python)) {
    throw "Python executable not found: $python"
}

& $python .\main.py --market --league $League --market-type "Currency,Fragments" --market-out-dir $OutputDir
