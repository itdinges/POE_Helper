# 0001 - Python CLI and local-first file model

- Status: Accepted
- Date: 2026-08-28

## Context

The project needs fast iteration and easy execution on Windows while dealing with POE2 filter text files in local user directories.

## Decision

- Use Python for the initial implementation.
- Start with a CLI interface before any UI layer.
- Operate on local files directly with explicit read/merge/write steps.
- Keep managed changes bounded by explicit start/end markers.

## Consequences

Positive:

- quick prototyping and iteration speed
- easy script execution from VS Code and terminal
- straightforward file I/O and text processing

Trade-offs:

- less discoverable UX vs a desktop UI
- profile logic in code can become rigid without config extraction

## Follow-ups

- Add config-driven profiles.
- Add tests for path resolution and idempotent merge behavior.
- Add dry-run mode for safer experimentation.
