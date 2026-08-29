# 0002 - Pluggable data adapters and trigger model

- Status: Accepted
- Date: 2026-08-29

## Context

The project currently combines filter operations and market operations through direct CLI flows. Upcoming features require multiple data sources, including optional authenticated account inventory, plus eventual UI consumption.

## Decision

- Introduce a layered architecture with separated domain and adapter concerns.
- Keep external data behind source adapters.
- Preserve manual trigger workflow now, while designing for scheduled refresh later.
- Standardize output contracts for CLI and future UI consumers.

## Consequences

Positive:

- Lower refactor risk when adding authenticated inventory data.
- Easier testing of domain logic independent of network/file APIs.
- Better long-term compatibility with UI and automation layers.

Trade-offs:

- Slightly more upfront structure.
- More files and interfaces to maintain.

## Follow-ups

- Add app/application orchestration module.
- Add app/contracts models for shared responses.
- Add tests based on fixture snapshots and route examples.
