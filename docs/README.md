# Documentation index

This folder holds the project background, architecture notes, runtime flow, and operational guidance.

## Reading order

### Overview

1. [Goals](architecture/GOALS.md)
2. [Architecture blueprint](architecture/ARCHITECTURE.md)
3. [How it works](architecture/HOW_IT_WORKS.md)
4. [Fetch type matrix](research/FETCH_TYPE_MATRIX.md)

### Operational context

5. [Project context and handoff](operations/PROJECT_CONTEXT.md)
6. [Roadmap](operations/ROADMAP.md)
7. [Handoff workflow](operations/HANDOFF_WORKFLOW.md)
8. [Review playbook](operations/REVIEW_PLAYBOOK.md)
9. [Test strategy](operations/TEST_STRATEGY.md)
10. [Coverage gaps report](reference/COVERAGE_GAPS.md)
11. [SQLite inspection guide](reference/SQL_INSPECTION_GUIDE.md)

### Reference

12. [ADR index](adr/README.md)

## Scope summary

In scope:

- local filter file discovery and managed output generation
- local market snapshot and normalization workflows
- broad utility market fetches such as Currency and core progression items
- build-aware equipment research as a contextual helper feature

Out of scope:

- direct game interaction or automation
- generic equipment-only market scraping for all item types
- anti-cheat or memory-based behavior

## Documentation intent

The docs are intentionally divided into:

- product intent and goals
- architecture and runtime flow
- operational notes and project continuity
- reference and validation material

This keeps the project readable without forcing every decision into one giant document.
