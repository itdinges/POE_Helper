# POE Helper

Local-first Path of Exile 2 helper focused on filter management, local market analysis, and build-aware planning support.

## Product intent

This project is a legal helper toolset, not gameplay automation.

The app is designed around two core layers:

- default universal market layer:
  - Currency
  - Fragments
  - Lineage Gems
  - Soul Cores
  - Idols
  - Runes
  - Liquid Emotions
  - Catalyst
  - Essences as secondary utility
- build-aware equipment layer:
  - character/class/ascendancy driven searches
  - craft base and item-mode discovery
  - similar-build comparison for gear planning

The default market layer is meant to stay stable and broadly useful. Equipment is treated as contextual and optional, not as a generic market fetch category.

## Architecture overview

The app currently follows a layered structure:

- CLI entrypoint: main.py
- application services: app/application/services.py
- domain logic: app/domain/scoring.py and app/domain/filter_profiles.py
- external adapters and parsers: app/market.py and app/adapters/market_adapter.py
- storage layer: app/infrastructure/market_store.py
- filter workflow: app/filter_manager.py
- shared DTOs: app/contracts/responses.py
- logging and observability: app/observability.py

This keeps the runtime flow clean:

- parse CLI arguments
- delegate to service orchestration
- normalize source data to internal models
- compute scores / comparisons / route logic
- persist useful snapshots locally
- generate managed filter output or recommendations

## Quickstart

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python main.py --list
```

## Current Commands

See [docs/commands/README.md](docs/commands/README.md) for the grouped command list.

Market snapshots are stored under `data/market` by default.

Notes:

- Conversion and flip simulations are chaos-normalized from the same snapshot.
- Route steps are defined in JSON and can model vendor chains.
- If an end currency is not in the market payload, route simulation reports it explicitly.
- Runtime logs are written to `data/logs/poe_helper.log` by default.
- The project intentionally keeps equipment work contextual and build-aware rather than treating all gear as a generic market feed.

## Documentation index

- Overview: [docs/architecture/GOALS.md](docs/architecture/GOALS.md)
- Architecture: [docs/architecture/ARCHITECTURE.md](docs/architecture/ARCHITECTURE.md)
- Runtime flow: [docs/architecture/HOW_IT_WORKS.md](docs/architecture/HOW_IT_WORKS.md)
- Market fetch decisions: [docs/research/FETCH_TYPE_MATRIX.md](docs/research/FETCH_TYPE_MATRIX.md)
- Project context: [docs/operations/PROJECT_CONTEXT.md](docs/operations/PROJECT_CONTEXT.md)
- Roadmap: [docs/operations/ROADMAP.md](docs/operations/ROADMAP.md)
- Review and QA: [docs/operations/REVIEW_PLAYBOOK.md](docs/operations/REVIEW_PLAYBOOK.md)
- Testing: [docs/operations/TEST_STRATEGY.md](docs/operations/TEST_STRATEGY.md)
- SQLite inspection: [docs/reference/SQL_INSPECTION_GUIDE.md](docs/reference/SQL_INSPECTION_GUIDE.md)
- Handoff workflow: [docs/operations/HANDOFF_WORKFLOW.md](docs/operations/HANDOFF_WORKFLOW.md)
- ADR index: [docs/adr/README.md](docs/adr/README.md)

This project is intentionally scoped to legal helper tooling and does not attempt to modify game behavior.
