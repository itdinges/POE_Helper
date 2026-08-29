param(
    [switch]$SkipSecurity,
    [switch]$SkipArchitecture
)

$ErrorActionPreference = "Stop"

function Run-Step {
    param(
        [string]$Name,
        [scriptblock]$Command
    )

    Write-Host "\n=== $Name ===" -ForegroundColor Cyan
    & $Command
    if ($LASTEXITCODE -ne 0) {
        throw "Step failed: $Name"
    }
}

$python = Join-Path $PSScriptRoot "..\.venv\Scripts\python.exe"
$python = [System.IO.Path]::GetFullPath($python)

if (-not (Test-Path $python)) {
    throw "Python interpreter not found at $python"
}

Run-Step "Unit Tests + Coverage" {
    & $python -m pytest -q --cov=app --cov-report=term-missing --cov-report=xml
}

Run-Step "Lint (Ruff critical rules)" {
    & $python -m ruff check . --select E9,F
}

if (-not $SkipSecurity) {
    Run-Step "Security Static Scan (Bandit)" {
        & $python -m bandit -q -r app
    }

    Run-Step "Dependency Audit (pip-audit)" {
        & $python -m pip_audit --desc --ignore-vuln GHSA-w596-4wvx-j9j6
    }
}

if (-not $SkipArchitecture) {
    Run-Step "Architecture Docs Presence" {
        $required = @(
            "docs/ARCHITECTURE.md",
            "docs/TEST_STRATEGY.md",
            "docs/PROJECT_CONTEXT.md",
            "docs/adr/README.md"
        )
        foreach ($path in $required) {
            if (-not (Test-Path $path)) {
                throw "Missing architecture document: $path"
            }
        }
        Write-Host "Architecture documentation check passed." -ForegroundColor Green
    }
}

Write-Host "\nAll review gate checks passed." -ForegroundColor Green
