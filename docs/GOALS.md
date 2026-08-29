# Goals

## Current Goal

Deliver a reliable local filter workflow for POE2:

- detect the correct OnlineFilters directory on Windows
- list available filter files (including extensionless files)
- generate a managed filter output with profile-specific rules
- keep generated output idempotent by replacing prior managed blocks
- mark output filter names with a _managed suffix for in-game selection clarity

## Near-Term Goals

- define and document stable architecture boundaries before major feature expansion
- add application-level interfaces that can be reused by a future UI
- add dry-run mode to preview changes before write
- add command to print available profiles
- move profile rules to JSON for easier editing without code changes
- add tests for directory resolution and managed block replacement

## Product Goals

- evolve into a practical POE2 planning assistant for filter, economy, and crafting decisions
- support optional account-aware planning: what do I have and what can I flip
- remain usable for non-technical users with minimal setup friction
- keep operations local-first and transparent

## Non-Goals For Now

- direct game interaction or input automation
- immediate implementation of authenticated account integrations
- broad feature scope before core reliability is proven
