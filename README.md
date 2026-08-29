# POE Helper

Local-first Path of Exile 2 helper focused on filter management and future economy/crafting assistance.

## Start Here

- Project docs: [docs/README.md](docs/README.md)
- Project handoff: [docs/PROJECT_CONTEXT.md](docs/PROJECT_CONTEXT.md)
- Goals: [docs/GOALS.md](docs/GOALS.md)
- How it works: [docs/HOW_IT_WORKS.md](docs/HOW_IT_WORKS.md)
- Roadmap: [docs/ROADMAP.md](docs/ROADMAP.md)
- ADR index: [docs/adr/README.md](docs/adr/README.md)
- Review playbook: [docs/REVIEW_PLAYBOOK.md](docs/REVIEW_PLAYBOOK.md)
- Coverage gaps report: [docs/COVERAGE_GAPS.md](docs/COVERAGE_GAPS.md)

## Quickstart

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python main.py --list
```

## Current Commands

```bash
python main.py --list
python main.py --build --source ERlx8msj --output ERlx8msj_managed --profile league_start
python main.py --list --dir .\temp
python main.py --market --league "Runes of Aldur" --market-type Currency
python main.py --market --league "Runes of Aldur" --market-type Currency --vendor-file config/vendor_prices.example.json --min-margin 0.05
python main.py --market --league "Runes of Aldur" --market-type Currency --convert --from-currency wisdom --to-currency chaos --amount 10000
python main.py --market --league "Runes of Aldur" --market-type Currency --flip-route-file config/flip_routes.example.json --flip-route-name wisdom_to_aug --amount 10000
python main.py --tail-logs --log-lines 80
python main.py --follow-logs --log-level DEBUG
```

Run tests:

```bash
python -m pytest -q
```

Run branch review gate:

```bash
powershell -ExecutionPolicy Bypass -File scripts/review_gate.ps1
```

Generate readable coverage backlog report:

```bash
powershell -ExecutionPolicy Bypass -File scripts/coverage_backlog_report.ps1
```

Market snapshots are stored under data/market by default.

Notes:

- Conversion and flip simulations are chaos-normalized from the same snapshot.
- Route steps are defined in JSON and can model vendor chains.
- If an end currency is not in the market payload (example: portal in some snapshots), route simulation reports it explicitly.
- Runtime logs are written to data/logs/poe_helper.log by default.

This project is intentionally scoped to legal helper tooling and does not attempt to modify game behavior.
