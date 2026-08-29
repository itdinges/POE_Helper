# How It Works

## Runtime Flow

1. CLI arguments are parsed in main.py.
2. FilterManager resolves a working filter directory:
   - explicit --dir if provided
   - otherwise best available default OnlineFilters location on Windows
3. The tool loads the source filter text.
4. The #name header is rewritten with a _managed suffix if needed.
5. Existing managed section markers are removed from the text.
6. Profile rules are appended in a new managed section.
7. The output file is written to disk.

## Managed Section Markers

The tool owns only this block:

- # ==== POE Helper managed section start ====
- # ==== POE Helper managed section end ====

Everything outside this block remains source-controlled by the base filter generator.

## Why Idempotency Matters

Re-running generation should not duplicate managed sections. The tool replaces the old managed block and writes exactly one updated block.

## Current Profiles

- mapping
- crafting
- league_start
