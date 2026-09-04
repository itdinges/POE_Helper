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
python main.py --market --league "Runes of Aldur" --market-type Currency --recommend
```

Web/API startup:

```bash
python main.py --api
python main.py --api --api-reload
```

Available API endpoints for the first slice:

- `GET /api/health`
- `GET /api/market/types`
- `GET /api/market/latest`
- `GET /api/market/history/{item_id}`
- `POST /api/market/refresh`

Frontend development:

```bash
cd frontend
npm install
npm run dev
```

Web POC launcher:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/start_web_poc.ps1
```

This starts the FastAPI backend on port `8000` and the Vue dev server on port `5173` in separate PowerShell windows.

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
- Holdings are now sourced from the local SQLite holdings table and edited through the web UI holdings panel.
- Recommendation mode defaults to `--source-currency exalt` and uses whole-unit trade sizing for buy/sell actions.
- Recommendation runs now auto-reuse the latest snapshot when it is <= 1 hour old, and auto-refetch when the latest snapshot is older than 1 hour.
- Recommendation output is focused on two tables: sell candidates (only items you own) and buy candidates (only items you can afford), both ordered by trend.