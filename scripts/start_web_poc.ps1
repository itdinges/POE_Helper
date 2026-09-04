param(
    [string]$ApiHost = "127.0.0.1",
    [int]$ApiPort = 8000,
    [string]$FrontendHost = "127.0.0.1",
    [int]$FrontendPort = 5173
)

$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
$python = Join-Path $root ".venv\Scripts\python.exe"
$frontendDir = Join-Path $root "frontend"

if (-not (Test-Path $python)) {
    throw "Python executable not found: $python"
}

if (-not (Test-Path $frontendDir)) {
    throw "Frontend directory not found: $frontendDir"
}


$backendCommand = @"
Set-Location '$root'
& '$python' main.py --api --api-host $ApiHost --api-port $ApiPort
"@

$frontendCommand = @"
Set-Location '$frontendDir'
npm run dev
"@

Write-Host "Starting POE Helper web POC..." -ForegroundColor Cyan
Write-Host "Backend:   http://$ApiHost`:$ApiPort" -ForegroundColor Cyan
Write-Host "Frontend:  http://$FrontendHost`:$FrontendPort" -ForegroundColor Cyan

Start-Process powershell -ArgumentList @(
    "-NoExit",
    "-ExecutionPolicy",
    "Bypass",
    "-Command",
    $backendCommand
)

Start-Process powershell -ArgumentList @(
    "-NoExit",
    "-ExecutionPolicy",
    "Bypass",
    "-Command",
    $frontendCommand
)

Write-Host "Launched backend and frontend in separate PowerShell windows." -ForegroundColor Green