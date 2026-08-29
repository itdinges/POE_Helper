# Project Context and Handoff

This document is the fast handoff for new chats. It captures the practical project state without needing full chat history.

## Product Intent

POE Helper is a local-first Path of Exile 2 assistant focused on filter workflow and future decision-support tooling.

## Current Milestone

Reliable managed-filter generation from existing POE2 online filters.

Implemented:

- auto-detect likely Windows OnlineFilters locations
- support extensionless filter filenames
- list source filters
- build managed output from a selected source
- append exactly one managed section (idempotent updates)
- suffix #name header with _managed for in-game selection clarity
- poe.ninja market snapshot fetch via league and type
- optional vendor-vs-market comparison from local JSON cost file
- two-way conversion between currency units via chaos normalization
- multi-step vendor route simulation with chaos PnL and ROI
- runtime observability with file logs plus tail/follow log commands

## Main CLI Flows

Local temp testing:

- .\\.venv\\Scripts\\python.exe .\\main.py --list --dir .\\temp
- .\\.venv\\Scripts\\python.exe .\\main.py --build --dir .\\temp --source ERlx8msj --output ERlx8msj_managed --profile league_start

Default live folder usage:

- .\\.venv\\Scripts\\python.exe .\\main.py --list
- .\\.venv\\Scripts\\python.exe .\\main.py --build --source ERlx8msj --output ERlx8msj_managed --profile league_start

Market data usage:

- .\\.venv\\Scripts\\python.exe .\\main.py --market --league "Runes of Aldur" --market-type Currency
- .\\.venv\\Scripts\\python.exe .\\main.py --market --league "Runes of Aldur" --market-type Currency --vendor-file config/vendor_prices.example.json --min-margin 0.05
- .\\.venv\\Scripts\\python.exe .\\main.py --market --league "Runes of Aldur" --market-type Currency --convert --from-currency wisdom --to-currency chaos --amount 10000
- .\\.venv\\Scripts\\python.exe .\\main.py --market --league "Runes of Aldur" --market-type Currency --flip-route-file config/flip_routes.example.json --flip-route-name wisdom_to_aug --amount 10000

Observability usage:

- .\\.venv\\Scripts\\python.exe .\\main.py --tail-logs --log-lines 80
- .\\.venv\\Scripts\\python.exe .\\main.py --follow-logs --log-level DEBUG

## Architecture Snapshot

Entry point:

- main.py parses CLI args and delegates orchestration to application services.

Core logic:

- app/filter_manager.py resolves working directory and performs read, merge, and write.
- Managed edits are bounded between explicit marker lines.
- Existing managed block is removed before writing a new one.
- app/market.py handles API fetch, snapshot persistence, summary output, and vendor comparison.
- app/market.py also handles normalized conversion math and route-based flip simulation.
- app/observability.py configures runtime logging and local log tail/follow behavior.
- app/application/services.py orchestrates workflows for filter and market commands.
- app/contracts/responses.py defines shared response models for CLI and future UI.

Profiles currently in code:

- mapping
- crafting
- league_start

## Guardrails and Scope

In scope:

- local file operations
- deterministic rule insertion
- transparent generated output

Out of scope:

- gameplay automation
- direct game process manipulation
- anti-cheat bypass techniques

## Known Environment Notes

- Multiple terminals may have different PATH visibility.
- Using the project venv interpreter path is the most reliable command path in this repo.
- OneDrive Documenten path can be the active OnlineFilters location.

## Next Priorities

1. Add dry-run mode and profile listing command.
2. Move profile rules to config file for easier editing.
3. Expand unit and integration tests beyond the initial service/orchestration baseline.
4. Prepare adapter split for optional authenticated inventory module.

## Testing Status

- Initial service/orchestration baseline tests implemented in tests/test_services.py.
- Current result: 22 passed with pytest.
- Branch readiness review gate script available at scripts/review_gate.ps1.
- Full review gate status: passing (coverage + ruff + bandit + pip-audit + architecture docs check).
- Current overall app coverage: 84%.

## Parked Feature

- Account-aware planning module:
	- answer what currencies/items the account currently has
	- combine holdings with route profitability to answer what can I flip now
	- implement later as an optional authenticated adapter after architecture and test foundations are in place

- Small long-running worker mode for periodic refresh:
	- currently parked until the system performs more than one fetch workflow
	- logging and follow mode already provide enough runtime visibility for now

## Update Rule

When behavior, architecture, or roadmap changes, update this file in the same commit so future chats stay aligned.
