# Roadmap

## Phase 1: Stable Filter Foundation

- done: local/default filter directory handling
- done: extensionless file support
- done: managed block insertion
- done: managed block replacement (idempotent)
- done: output name suffixing for in-game clarity
- next: dry-run and profile listing commands

## Phase 2: Architecture and Contracts

- done: define application service layer for orchestration
- done: define contract models for CLI and future UI responses
- done: keep adapter boundaries between domain logic and external data sources
- next: add explicit manual trigger flow abstraction and scheduling-ready hooks

## Phase 3: Config-Driven Rules

- load profiles from JSON/YAML
- allow profile composition (example: league_start + crafting)
- validation for malformed or conflicting rules

## Phase 4: Data-Aware Suggestions

- market snapshot ingestion
- route scanner for profitable flips
- optional value thresholds for show/hide highlighting
- profile presets for leveling, mapping, and crafting focus
- optional account-aware planning module (authenticated, read-only)

## Phase 5: Usability

- lightweight desktop or web UI
- import/export settings
- guardrails and diagnostics for path and file issues

## Phase 6: Test and Quality Gates

- done: baseline review gate script for coverage, lint, security, and architecture docs presence
- fixture-driven unit tests for parser and conversion logic
- integration tests for file workflows and command outputs
- optional live endpoint smoke tests behind explicit marker

## Parked Backlog

- small long-running worker mode for periodic refresh and continuous pipelines
	- reason parked: current system behavior is mostly one-shot fetch commands
	- revisit when orchestrating multi-source and scheduled workflows

## Open Questions

- How much rule customization should stay in code vs config?
- Should generated outputs include profile metadata beyond #name suffix?
- Which market sources are stable enough for low-maintenance integration?
