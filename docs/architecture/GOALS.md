# Goals

## Current Goal

Deliver a reliable local filter workflow for POE2:

- detect the correct OnlineFilters directory on Windows
- list available filter files (including extensionless files)
- generate a managed filter output with profile-specific rules
- keep generated output idempotent by replacing prior managed blocks
- mark output filter names with a _managed suffix for in-game selection clarity

## Core Market Goal

Build a stable default fetch layer for broadly useful economy data:

- Currency
- Fragments
- Lineage Gems
- Soul Cores
- Idols
- Runes
- Liquid Emotions
- Catalyst
- Essences as a secondary utility category

These should be the default fetch set because they provide broad utility across many play patterns and are much more stable than a generic equipment feed.

## Equipment Goal

Keep equipment support intentionally build-focused rather than universal:

- search and compare gear based on character type / class / ascendancy
- compare against similar builds and common item patterns
- identify craft bases and useful item modes to search for on the trade market
- support item discovery for build planning instead of treating gear as a generic market category

This makes equipment a build helper feature, not a default market-fetch feature.

## Near-Term Goals

- define and document stable architecture boundaries before major feature expansion
- add application-level interfaces that can be reused by a future UI
- add dry-run mode to preview changes before write
- add command to print available profiles
- move profile rules to JSON for easier editing without code changes
- add tests for directory resolution and managed block replacement
- validate the default universal fetch categories against real market payloads
- define the optional build-aware equipment workflow separate from the default economy pipeline

## Product Goals

- evolve into a practical POE2 planning assistant for filter, economy, crafting, and build-focused gear decisions
- support optional account-aware planning: what do I have and what can I flip
- keep the default market layer focused on broadly useful, low-noise categories
- keep equipment analysis contextual and build-aware instead of noisy and over-generic
- remain usable for non-technical users with minimal setup friction
- keep operations local-first and transparent

## Non-Goals For Now

- direct game interaction or input automation
- broad generic equipment market scraping for every item type
- immediate implementation of authenticated account integrations
- broad feature scope before core reliability is proven
