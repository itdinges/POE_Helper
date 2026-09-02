# Fetch type matrix

This document is the decision guide for choosing which market data types are worth fetching before we expand the app further.

The purpose is not to fetch everything blindly. The purpose is to decide which data sources and market types are useful, stable, and aligned with the current local-first helper scope.

## Current product intent

The project is intentionally scoped to:

- local-first market analysis
- filter assistance and managed filter generation
- item/value recommendations
- route and margin-style decision support

It is not a broad market scraping platform or a game automation system.

## Decision criteria

A market type is a good candidate if it is:

- available from the source API in a stable shape
- easy to normalize into a common record model
- useful for pricing, scoring, or filtering decisions
- relevant to the item categories that matter in normal PoE play

A market type is a weak candidate if it is:

- sparse or unstable
- poorly normalized across leagues or patches
- noisy enough to reduce scoring quality
- not useful for the current helper workflow

## Base universal fetch set

These are the core categories we should treat as the default, broadly useful fetch set:

### 1) Currency

Why it matters:
- core for conversion and route simulations
- easy to compare in chaos terms
- highly useful for vendor and flip analysis

Project fit:
- strong fit
- already a core market workflow area

Risk:
- some currencies may be missing from certain payloads
- requires normalizing conversion rates correctly

### 2) Fragments

Why it matters:
- strong league utility and progression value
- usually relevant across many builds and playstyles
- good for broad value discovery without heavy build filtering

Project fit:
- strong fit

Risk:
- still benefits from filtering for actual value relevance

### 3) Lineage Gems

Why it matters:
- generally useful as a market category with clear demand patterns
- relevant to broad planning and filter guidance

Project fit:
- strong fit

Risk:
- may need category-specific filtering depending on league and meta

### 4) Soul Cores

Why it matters:
- often strongly relevant to general progression and crafting value
- good candidate for universal fetch because of broad demand patterns

Project fit:
- strong fit

Risk:
- usefulness depends on league economy and active crafting loops

### 5) Idols

Why it matters:
- broad utility and strong trade signal in many gameplay windows
- good fit for general decision-support workflows

Project fit:
- strong fit

Risk:
- value depends on the current active archetype mix

### 6) Runes

Why it matters:
- common utility item category with strong general market interest
- good for broad recommendation logic

Project fit:
- strong fit

Risk:
- can be noisy if too many variants are treated the same way

### 7) Liquid Emotions

Why it matters:
- useful utility market category with clear value signal
- works well as a default fetch item for general help

Project fit:
- strong fit

Risk:
- category-specific price behavior still needs validation

### 8) Catalyst

Why it matters:
- standard trade utility with repeated demand patterns
- generally strong fit for general-purpose market analysis

Project fit:
- strong fit

Risk:
- value depends on recipe and craft demand in the active league

### 9) Essences

Why it matters:
- common utility category with a lot of repeated demand
- useful in market comparison and craft planning
- can be very low-cost, but still relevant if the project is measuring practical value instead of only high-margin spikes

Project fit:
- useful but secondary in the default fetch set

Risk:
- often cheap and less exciting than core currencies, so they should not dominate scoring without filters

## Recommended order of evaluation

This is the practical order to validate fetch readiness:

1. Currency
2. Fragments
3. Lineage Gems
4. Soul Cores
5. Idols
6. Runes
7. Liquid Emotions
8. Catalyst
9. Essences

Reasoning:
- these are the broadest, most generally useful categories for a helper app
- they are better default candidates than trying to model every equipment style at once
- they give good value for scoring and filter generation without overfitting to one build or one meta snapshot

## Recommended core scope

For the near-term app, the best minimal default scope is:

- Currency
- Fragments
- Lineage Gems
- Soul Cores
- Idols
- Runes
- Liquid Emotions
- Catalyst
- Essences as a secondary/optional utility category

This keeps the app useful while avoiding the noise and instability of large equipment-heavy fetches.

## Equipment is intentionally separate

Equipment should not be treated as part of the universal base set.

Why:
- price variance is usually much higher across league balance changes
- build archetype matters a lot
- class/ascendancy-specific demand makes generic scoring noisy
- a strong equipment fetch should be profile-driven instead of globally default

Equipment is better modeled as:

- contextual market analysis
- profile-aware filtering
- optional class or build-specific recommendations

## Validation checklist for each type

Before a type is considered approved:

- does the external source return a stable payload shape?
- does normalization produce valid item_id, item_name, chaos_value, and primary_value?
- do rows persist cleanly to SQLite?
- does the scoring layer produce useful values without excessive noise?
- does the filter profile generation remain readable and deterministic?
- are there any gaps or malformed entries that need explicit handling?

## Current recommendation

The app should treat the universal core set above as the first production-ready fetch target set.

Once that set is stable and inspected in SQLite, we can decide whether to add equipment-oriented fetches behind profile-aware rules instead of trying to load the whole equipment market as a default.

## Short conclusion

For a default helper app, the most useful fetch categories are the utility and economy items that stay broadly relevant across many builds and play patterns:

- Currency
- Fragments
- Lineage Gems
- Soul Cores
- Idols
- Runes
- Liquid Emotions
- Catalyst
- Essences as a secondary value category

Equipment should remain a contextual, optional layer rather than a universal default.

## Recommended order of evaluation

This is the practical order to validate fetch readiness:

1. Currency
2. Fragment
3. DivinationCard
4. Essence
5. Map
6. Gem
7. UniqueWeapon / UniqueAccessory and other unique item families

Reasoning:
- Currency is the cleanest first proof of the pipeline.
- The next categories validate whether the generic normalization logic scales beyond a single type.
- Unique and broader item groups are valuable, but they are higher-risk and should be validated after the base pipeline is stable.

## Scope recommendation

For the near-term app, the best minimal scope is:

- Currency first
- maybe one or two additional categories only after the base pipeline is proven

This avoids trying to ingest and score every possible market category before the core data model is stable.

## Validation checklist for each type

Before a type is considered approved:

- does the external source return a stable payload shape?
- does normalization produce valid item_id, item_name, chaos_value, and primary_value?
- do rows persist cleanly to SQLite?
- does the scoring layer produce useful values without excessive noise?
- does the filter profile generation remain readable and deterministic?
- are there any gaps or malformed entries that need explicit handling?

## Current recommendation

The app should treat Currency as the primary live-fetch target for the first production-ready pass.

Once the Currency pipeline is stable and inspected in SQLite, we can expand to the next categories with a clear matrix-based decision process instead of grabbing all market types at once.

## Short conclusion

The fetch matrix should answer one question clearly:

Which market types are useful, stable, and worth the scoring/filtering effort for this app?

For now, the answer is:

- start with Currency
- validate additional categories after the base ingestion path is proven
- avoid broad ingestion until the data model is stable
