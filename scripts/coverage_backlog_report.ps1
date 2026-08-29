param(
    [string]$CoverageXmlPath = "coverage.xml",
    [string]$OutputPath = "docs/COVERAGE_GAPS.md"
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path $CoverageXmlPath)) {
    throw "Coverage XML not found at $CoverageXmlPath. Run tests with coverage first."
}

[xml]$coverage = Get-Content $CoverageXmlPath
$classes = @($coverage.coverage.packages.package.classes.class)

$rows = @()
foreach ($class in $classes) {
    $rawFilename = [string]$class.filename
    $filename = $rawFilename.Replace("\", "/")
    if (-not $filename.StartsWith("app/")) {
        $filename = "app/$filename"
    }
    if ($filename.EndsWith("/__init__.py")) {
        continue
    }
    $lines = @($class.lines.line)
    if ($lines.Count -eq 0) {
        continue
    }

    $stmt = $lines.Count
    $missed = @($lines | Where-Object { [int]$_.hits -eq 0 })
    $miss = $missed.Count
    $covered = $stmt - $miss
    $pct = [Math]::Round(($covered / $stmt) * 100, 1)

    $missingLinePreview = ($missed | Select-Object -First 10 | ForEach-Object { $_.number }) -join ", "
    if (-not $missingLinePreview) {
        $missingLinePreview = "-"
    }

    $rows += [PSCustomObject]@{
        File = $filename
        Statements = $stmt
        Missed = $miss
        Coverage = $pct
        MissingPreview = $missingLinePreview
    }
}

$rows = $rows | Sort-Object Coverage, File
$totalStmt = ($rows | Measure-Object Statements -Sum).Sum
$totalMiss = ($rows | Measure-Object Missed -Sum).Sum
$totalCov = if ($totalStmt -gt 0) { [Math]::Round((($totalStmt - $totalMiss) / $totalStmt) * 100, 1) } else { 0 }

$timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
$targetText = @(
    "- Current baseline target: no hard fail-under yet (informational tracking).",
    "- Near-term target: 45%+ overall coverage.",
    "- Next target: 55%+ overall with market and filter modules improved.",
    "- Longer-term target: 70%+ once module boundaries stabilize."
)

$gaps = $rows | Where-Object { $_.Coverage -lt 60 }

$linesOut = @()
$linesOut += "# Coverage Gaps Report"
$linesOut += ""
$linesOut += "Generated: $timestamp"
$linesOut += ""
$linesOut += "## Summary"
$linesOut += ""
$linesOut += "- Overall coverage: $totalCov%"
$linesOut += "- Total statements: $totalStmt"
$linesOut += "- Total missed: $totalMiss"
$linesOut += ""
$linesOut += "## Coverage Growth Targets"
$linesOut += ""
$linesOut += $targetText
$linesOut += ""
$linesOut += "## Priority Gaps (Coverage < 60%)"
$linesOut += ""

if ($gaps.Count -eq 0) {
    $linesOut += "- None"
} else {
    foreach ($row in $gaps) {
        $linesOut += "- $($row.File): $($row.Coverage)% (missed $($row.Missed)/$($row.Statements)); sample missing lines: $($row.MissingPreview)"
    }
}

$linesOut += ""
$linesOut += "## Full Module Coverage"
$linesOut += ""
$linesOut += "| File | Coverage | Missed / Statements |"
$linesOut += "| --- | ---: | ---: |"
foreach ($row in $rows) {
    $linesOut += "| $($row.File) | $($row.Coverage)% | $($row.Missed) / $($row.Statements) |"
}

$targetDir = Split-Path -Parent $OutputPath
if ($targetDir -and -not (Test-Path $targetDir)) {
    New-Item -ItemType Directory -Path $targetDir | Out-Null
}

Set-Content -Path $OutputPath -Value ($linesOut -join "`n") -Encoding UTF8
Write-Host "Coverage backlog report written to $OutputPath"
