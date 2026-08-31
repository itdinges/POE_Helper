# Critical bugs and required fixes

## High-severity findings from Bugbot

### 1) Recommendation ranking is mathematically arbitrary

Location: app/market.py around the recommendation sort.

Problem:

- the code sorts by value_divine
- but value_chaos and value_divine are effectively amount * source_price for each target
- every target can therefore collapse to a constant or near-constant ranking signal

Result:

- recommendation ordering is not meaningful
- the output appears plausible but does not reflect actual conversion quality

### 2) Filter generation emits invalid loot-filter syntax

Location: app/domain/filter_profiles.py

Problem:

- generated output uses Class with item display names and a Watch block
- valid loot-filter grammar expects Show/Hide blocks and names on BaseType
- Class is an item class such as Currency, not a specific item name

Result:

- the generated filter text will not match scored items in-game
- tests currently lock in the wrong behavior instead of the real grammar

## Fix direction

### For recommendation ranking

Use a sort key that varies by target and can be explained to a player, such as:

- units received per chaos
- implied rate or efficiency score
- spread or inventory-slot-adjusted value

The key should not be a constant derived from the same price multiplication for all rows.

### For filter generation

Use legal filter semantics:

- Show/Hide rules only
- BaseType for item names
- legal class names only when intentionally targeting a class
- no Watch block unless it is a valid filter action for the intended filter format

## Testing requirement

The failing test should encode actual loot-filter grammar, not just string grouping. The review calls this out as especially important because the current tests currently assert the invalid output.

## Why it matters

These are not cosmetic bugs. They break the newest decision-support surfaces and make the tool appear more useful than it really is.
