# Architecture Blueprint

This document defines the target architecture before deeper feature work.

## Design Goals

- Keep core logic deterministic and testable.
- Isolate external data sources behind adapters.
- Support both manual triggers now and scheduled refresh later.
- Provide stable interfaces that a future UI can consume without refactors.

## High-Level Layers

1. Interface Layer
- CLI commands now.
- Future HTTP or desktop UI adapter later.

2. Application Layer
- Use-cases and orchestration.
- Examples: build filter, fetch market snapshot, evaluate flip routes.

3. Domain Layer
- Pure calculations and decisions.
- Examples: currency conversion, route simulation, profitability scoring.

4. Infrastructure Layer
- File system, HTTP clients, cache store, config loader.
- No business decisions here.

## Module Split Proposal

- app/filter_manager.py
  - Filter file read/merge/write and managed block operations.
- app/market.py
  - Market data parsing, conversion math, route simulation.
- app/application/
  - Orchestration services for commands and workflows.
- app/adapters/
  - External source adapters:
    - poe_ninja_adapter
    - poe_trade_adapter (future, authenticated)
    - account_inventory_adapter (future, authenticated)
- app/contracts/
  - Shared request/response models for CLI and future UI.

## Data Source Strategy

Primary source now:
- poe.ninja exchange overview, read-only snapshots.

Planned source (parked for later):
- Authenticated account/inventory source to answer:
  - what do I have
  - what can I flip with current inventory

Rule:
- Domain code should never depend on one source format directly.
- Adapters map source payloads into shared internal models.

## Trigger Strategy

Stage 1: Manual trigger
- User runs command.
- Command fetches current data and computes output.

Stage 2: Scheduled trigger
- Configurable polling intervals per source.
- Cache with freshness windows and retry policy.
- UI receives latest stable snapshot.

Stage 3: Event-style updates
- Push new calculations only when material changes occur.
- Avoid noisy recomputation.

## Runtime Observability

Requirements:

- backend actions must emit structured logs with timestamps and module names
- logs must be visible in real time during execution
- logs must be persisted to local files for post-run diagnosis

Current implementation direction:

- default log file output under data/logs/
- CLI commands to tail and follow logs, similar to container log attach behavior
- optional DEBUG level for deep parsing and conversion diagnostics

## Interface Contract for Future UI

Every workflow should return a typed response model with:

- metadata:
  - source name
  - fetched timestamp
  - snapshot id
- data:
  - rows, opportunities, route simulations
- diagnostics:
  - warnings, missing symbols, stale data flags

This keeps CLI, API, and UI aligned.

## Reliability Rules

- All calculations should be reproducible from a saved snapshot.
- No silent fallback that changes semantics.
- Explicit error messages for missing currencies or incomplete routes.
- Keep generated artifacts and user configs separate.

## Security and Privacy Constraints

- Auth credentials must stay in environment variables.
- Never write secrets to logs.
- Keep authenticated features read-only by default.
- Rate limit all authenticated requests.

## Implementation Order

1. Keep current CLI behavior stable.
2. Extract orchestration from main into application services.
3. Define shared response models in contracts.
4. Add schedule-ready refresh coordinator.
5. Add authenticated inventory adapter as optional module.
