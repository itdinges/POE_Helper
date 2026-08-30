# Commands

This folder collects the runnable entry points for the project. The goal is to keep the commands close together without making any single document too large.

## Filter Workflows

Run these from the project root:

```bash
python main.py --list
python main.py --list --dir .\temp
python main.py --build --source ERlx8msj --output ERlx8msj_managed --profile league_start
python main.py --build --dir .\temp --source ERlx8msj --output ERlx8msj_managed --profile league_start
```

## Market Workflows

Starter fetch for the current database-fill test path:

- Use only `Currency` and `Fragments`.
- This is the small validation slice for checking fetch, normalization, and SQLite writes together.

```bash
python main.py --market --league "Runes of Aldur" --market-type Currency,Fragments
```

Default utility fetch set:

```bash
python main.py --market --league "Runes of Aldur" --market-type all
```

Other market helpers:

```bash
python main.py --market --league "Runes of Aldur" --market-type Currency --vendor-file config/vendor_prices.example.json --min-margin 0.05
python main.py --market --league "Runes of Aldur" --market-type Currency --convert --from-currency wisdom --to-currency chaos --amount 10000
python main.py --market --league "Runes of Aldur" --market-type Currency --flip-route-file config/flip_routes.example.json --flip-route-name wisdom_to_aug --amount 10000
python scripts/fetch_market_starter.ps1
python scripts/market_catalog_helper.py
```

Starter sample collection:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/fetch_market_samples.ps1
```

Database reset for dev/test:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/reset_market_database.ps1
```

## Logs and Quality

```bash
python main.py --tail-logs --log-lines 80
python main.py --follow-logs --log-level DEBUG
python -m pytest -q
powershell -ExecutionPolicy Bypass -File scripts/review_gate.ps1
```

## Reports and Handoffs

```powershell
powershell -ExecutionPolicy Bypass -File scripts/coverage_backlog_report.ps1
powershell -ExecutionPolicy Bypass -File scripts/eod_handoff.ps1 -Notes "what changed and what is next"
```

## Notes

- `Currency,Fragments` is the small starter slice for validating that the fetch, normalization, and SQLite write path all work together.
- `all` expands to the config-backed default utility catalog.
- Resetting the local database is safe for dev and test use because it only clears the local SQLite file contents.