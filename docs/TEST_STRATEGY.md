# Test Strategy

This project needs confidence in conversion math, filter generation, and data parsing before UI growth.

## Test Pyramid

1. Unit tests
- Fast, deterministic, no network.
- Validate pure logic and edge cases.

2. Integration tests
- File system and parser integration.
- Optional network tests behind explicit marker.

3. Smoke tests
- CLI command-level checks for key workflows.

## Unit Test Targets

Filter workflow:
- managed block insertion
- idempotent replacement
- #name managed suffix behavior
- path resolution selection logic

Market workflow:
- payload parsing into internal rows
- chaos normalization and conversion math
- route simulation PnL and ROI
- missing-currency error behavior

Config and validation:
- vendor file parsing
- route file schema checks

## Integration Test Targets

- Build managed filter from fixture input to output fixture.
- Snapshot file writing with deterministic naming pattern checks.
- End-to-end market command using recorded fixture payloads.

## Network Testing Policy

- Default test suite should not call live endpoints.
- Store sample market payload fixtures under tests/fixtures.
- Add optional live test marker for manual verification only.

## Suggested Tooling

- pytest
- pytest-cov
- responses or requests-mock for HTTP stubs

## Initial Test File Plan

- tests/test_filter_manager.py
- tests/test_market_parsing.py
- tests/test_conversion_and_routes.py
- tests/test_cli_smoke.py
- tests/fixtures/poe_ninja_currency_overview.json

## Definition of Done for New Features

A feature is done when:

- unit tests cover happy path and failure modes
- integration test covers file or adapter boundary
- docs are updated in PROJECT_CONTEXT and roadmap if behavior changed
