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
python main.py --market --league "Runes of Aldur" --market-type Currency --recommend --holdings-file config/holdings.example.json
```

OAuth Currency Exchange setup and run:

```bash
python main.py --oauth-setup
python main.py --market --market-source oauth_cx --market-type Currency
```

For `oauth_cx`, fill `oauth.client_id` and `oauth.client_secret` in [config/settings.json](config/settings.json).
Use your PoE account applications page to create/manage confidential client credentials:

- https://www.pathofexile.com/my-account/applications

Note: `/oauth/authorize` is primarily for user-consent authorization-code flows; this project's `service:cxapi` fetch currently uses `/oauth/token` with `client_credentials`.

Manual holdings file format example:

```json
{
	"Divine Orb": 12,
	"Exalted Orb": 48,
	"Chaos Orb": 840
}
```

Use `config/holdings.example.json` as a starter template.

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
- Holdings are currently manual JSON input only. Live stash/account sync with PoE2 authentication is intentionally out of scope until a stable API path is available.
- Recommendation mode defaults to `--source-currency exalt` and uses whole-unit trade sizing for buy/sell actions.
- Recommendation runs now auto-reuse the latest snapshot when it is <= 1 hour old, and auto-refetch when the latest snapshot is older than 1 hour.
- Recommendation output is focused on two tables: sell candidates (only items you own) and buy candidates (only items you can afford), both ordered by trend.