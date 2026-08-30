param(
    [string]$League = "Runes of Aldur",
    [string]$OutputDir = "data/raw/market_samples",
    [string]$ConfigPath = "config/market_types.json",
    [switch]$IncludeOptional,
    [switch]$IncludeProgression,
    [switch]$IncludeEquipment
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path $ConfigPath)) {
    throw "Missing config file: $ConfigPath"
}

$config = Get-Content -Raw -Path $ConfigPath | ConvertFrom-Json
$types = @($config.default_types)

if ($IncludeOptional) {
    $types += @($config.optional_types)
}

if ($IncludeProgression) {
    $types += @($config.progression_types)
}

if ($IncludeEquipment) {
    $types += @($config.equipment_types)
}

$types = $types | Where-Object { $_ } | Select-Object -Unique

$baseUrl = "https://poe.ninja/poe2/api/economy/exchange/current/overview"
$targetDir = Join-Path (Get-Location) $OutputDir
New-Item -ItemType Directory -Force -Path $targetDir | Out-Null

foreach ($type in $types) {
    $safeName = $type.Replace(" ", "_")
    $fileName = "{0}_{1}.json" -f ($League.Replace(" ", "_"), $safeName)
    $filePath = Join-Path $targetDir $fileName

    $encodedLeague = [System.Net.WebUtility]::UrlEncode($League)
    $encodedType = [System.Net.WebUtility]::UrlEncode($type)

    Write-Host "Fetching $type ..."
    $uri = "{0}?league={1}&type={2}" -f $baseUrl, $encodedLeague, $encodedType
    $response = Invoke-RestMethod -Uri $uri -Method Get

    $response | ConvertTo-Json -Depth 10 | Set-Content -Path $filePath -Encoding UTF8
    Write-Host "Saved $filePath"
}

Write-Host "Download complete. Types fetched: $($types.Count)"
