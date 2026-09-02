param(
    [string]$OutputPath = "docs/operations/SESSION_HANDOFF.md",
    [string]$Notes = ""
)

$ErrorActionPreference = "Stop"

function Safe-Git {
    param([string[]]$CommandArgs)
    try {
        $result = & git @CommandArgs 2>$null
        if ($LASTEXITCODE -ne 0) {
            return ""
        }
        return ($result | Out-String).TrimEnd()
    }
    catch {
        return ""
    }
}

$timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
$branch = Safe-Git @("branch", "--show-current")
$head = Safe-Git @("rev-parse", "--short", "HEAD")
$status = Safe-Git @("status", "--short")
$recentCommits = Safe-Git @("log", "--oneline", "-5")

if (-not $status) {
    $status = "(clean working tree)"
}
if (-not $recentCommits) {
    $recentCommits = "(no commits found)"
}
if (-not $branch) {
    $branch = "(unknown)"
}
if (-not $head) {
    $head = "(unknown)"
}

$coverageSummary = "(not generated yet)"
if (Test-Path "docs/reference/COVERAGE_GAPS.md") {
    $summaryLines = Get-Content "docs/reference/COVERAGE_GAPS.md" | Select-String "Overall coverage|Total statements|Total missed"
    if ($summaryLines) {
        $coverageSummary = ($summaryLines | ForEach-Object { $_.Line.Trim() }) -join "`n"
    }
}

$nextPriorities = @()
if (Test-Path "docs/operations/PROJECT_CONTEXT.md") {
    $lines = Get-Content "docs/operations/PROJECT_CONTEXT.md"
    $start = ($lines | Select-String "^## Next Priorities").LineNumber
    if ($start) {
        for ($i = $start; $i -lt $lines.Count; $i++) {
            $line = $lines[$i]
            if ($line -match "^## ") { break }
            if ($line.Trim()) { $nextPriorities += $line }
        }
    }
}

if ($nextPriorities.Count -eq 0) {
    $nextPriorities = @("1. Update docs/PROJECT_CONTEXT.md with next priorities.")
}

$notesText = if ($Notes.Trim()) { $Notes.Trim() } else { "(add optional notes via -Notes)" }

$content = @()
$content += "# Session Handoff"
$content += ""
$content += "Generated: $timestamp"
$content += ""
$content += "## Repo State"
$content += ""
$content += "- Branch: $branch"
$content += "- HEAD: $head"
$content += ""
$content += "### Working Tree"
$content += ""
$content += '```text'
$content += $status
$content += '```'
$content += ""
$content += "### Recent Commits"
$content += ""
$content += '```text'
$content += $recentCommits
$content += '```'
$content += ""
$content += "## Coverage Snapshot"
$content += ""
$content += '```text'
$content += $coverageSummary
$content += '```'
$content += ""
$content += "## Next Priorities"
$content += ""
$content += $nextPriorities
$content += ""
$content += "## Operator Notes"
$content += ""
$content += $notesText
$content += ""
$content += "## Quick Restart Checklist"
$content += ""
$content += "1. Read docs/operations/SESSION_HANDOFF.md"
$content += "2. Read docs/operations/PROJECT_CONTEXT.md"
$content += "3. Run tests: python -m pytest -q"
$content += "4. Run review gate when ready: powershell -ExecutionPolicy Bypass -File scripts/review_gate.ps1"

$targetDir = Split-Path -Parent $OutputPath
if ($targetDir -and -not (Test-Path $targetDir)) {
    New-Item -ItemType Directory -Path $targetDir | Out-Null
}

Set-Content -Path $OutputPath -Value ($content -join "`n") -Encoding UTF8
Write-Host "Session handoff written to $OutputPath"
