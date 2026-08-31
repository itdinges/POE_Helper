# Architecture and workflow gaps

## 1) Product loops are disconnected

The intended flow is:

fetch -> persist -> score from history -> advise conversions -> optionally rewrite a managed filter

The actual CLI flow is still incomplete:

- market fetch always hits the network for requested types
- recommendation and conversion logic often operate only on the first successful payload
- multi-type fetch output blends types together but downstream logic ignores later entries
- scoring is not yet orchestrated in the main workflow
- filter generation is not wired in as a real player command
- historical data is mostly present but not yet used within a main UX path

## 2) app/market.py is still the gravity well

This file mixes:

- HTTP fetch logic
- snapshot persistence
- parsing
- conversion math
- recommendation ranking
- vendor comparison
- route simulation

This fights the intended architecture: adapters should isolate external data, and domain logic should remain cleaner and more testable.

A healthier split would be:

- adapters/poe_ninja.py for HTTP and snapshot handling
- domain/market_parse.py for payload-to-row parsing
- domain/conversion.py for pricing and recommendation rules
- domain/routes.py for route simulation

## 3) Scoring is still a rough draft

The current score formula is too simple for the product goal:

- delta percent and margin are combined crudely
- results can drift toward simplistic watch/hide decisions
- vendor-aware comparisons still act on absolute chaos margin without normalizing for scale or value

This is useful as a first pass, but it is not yet a meaningful affordability and repeatability signal.

## 4) Filter profiles are still placeholders

The in-code profiles are small and only loosely mapped to POE2 semantics.

This is acceptable as a merge proof, but not as a product-quality profile layer. It should not be treated as a real player-facing mapping until valid game grammar and taxonomy are in place.

## 5) Operational reliability gaps

The review calls out several important weaknesses:

- all-type fetch fails fast on the first broken type
- there is no offline snapshot-driven recommendation command
- no retry/backoff or user-agent discipline for repeated fetches
- SQLite uniqueness uses second-level precision and can collide within the same second
- pydantic is present but not used, which creates unclear contract expectations
- league default is hard-coded and will rot over time

## Review conclusion

The codebase is showing the shape of the right architecture, but the operational flow and separation of concerns still need to become real before the app is usable as a daily helper.
