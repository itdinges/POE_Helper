param(
    [string]$League,
    [string]$ConfigPath = "config/settings.json",
    [string]$OutputDir = "data/market"
)

$ErrorActionPreference = "Stop"

# Starter path for the database-fill test using config-driven defaults.

$root = Split-Path -Parent $PSScriptRoot
$python = Join-Path $root ".venv\Scripts\python.exe"

if (-not (Test-Path $python)) {
    throw "Python executable not found: $python"
}

if ([string]::IsNullOrWhiteSpace($League)) {
    $settingsPath = Join-Path $root $ConfigPath
    if (-not (Test-Path $settingsPath)) {
        throw "Settings file not found: $settingsPath"
    }

    $settings = Get-Content -Path $settingsPath -Raw | ConvertFrom-Json
    if (-not $settings.league -or [string]::IsNullOrWhiteSpace([string]$settings.league)) {
        throw "Missing 'league' in settings file: $settingsPath"
    }

    $League = [string]$settings.league
}

& $python .\main.py --market --league $League --market-type "all" --market-out-dir $OutputDir
