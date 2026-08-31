# Product intent and scope

## The core product story

POE Helper is meant to be a local-first Path of Exile 2 planning assistant, not a bot and not a generic market scraper.

The intended player loop is:

1. During campaign play, keep a loot filter that highlights what matters.
2. Take read-only market snapshots so history exists before Currency Exchange matters.
3. After Currency Exchange unlocks, use history to judge affordable and repeatable conversions.
4. Later, support build-aware gear planning as a distinct optional layer.

## Product layers

| Layer | Role | Examples |
| --- | --- | --- |
| Default utility market | Stable, broadly useful economy data | Currency, Fragments, Lineage Gems, Soul Cores, Idols, Runes, Liquid Emotions, Catalyst, Essences |
| Build-aware equipment | Optional contextual planning layer | Trade-site style search, similar-build comparison |

## Hard non-goals

- no gameplay automation or process injection
- no anti-cheat-adjacent work
- no default authenticated account scraping
- no dumping the entire equipment market into the default catalog

## Why this matters

The repo is strongest when it stays local-first and conservative. The architecture should treat the current CLI as a stage 1 interface, with typed outputs that can later power a GUI or other client.

## Review takeaway

The product intent is clear and healthy. The risk is not in the vision; it is in letting the code drift toward broader unsupported features without first proving the core loop.
