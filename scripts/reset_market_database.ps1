param(
    [string]$DatabasePath = "data/market/poe_market.db"
)

$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
$python = Join-Path $root ".venv\Scripts\python.exe"

if (-not (Test-Path $python)) {
    throw "Python executable not found: $python"
}

& $python -c @"
from app.infrastructure.market_store import SQLiteMarketStore
store = SQLiteMarketStore(r'$DatabasePath')
store.reset_database()
store.close()
print('Database reset complete.')
"@
