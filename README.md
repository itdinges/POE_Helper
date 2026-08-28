# POE Helper

A small Python project for building a Path of Exile 2 helper focused on practical tools such as:

- loot filter management
- market-aware rule suggestions
- crafting value helpers
- build progression reminders

## Current focus

The first milestone is a local filter helper that can:

- read a POE 2 online filter file
- merge in custom rules
- save a new filter into the Windows `OnlineFilters` folder
- support multiple profiles for different builds or league phases

## Windows filter location

Path of Exile 2 online filters are typically stored under:

`C:\Users\<you>\Documents\My Games\Path of Exile 2\OnlineFilters`

## Project structure

- `app/` - Python package for helpers and logic
- `main.py` - entry point
- `requirements.txt` - Python dependencies

## Getting started

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

## CLI usage

List available filter files in the POE 2 OnlineFilters folder:

```bash
python main.py --list
```

Build a managed filter by appending a profile-specific rule section:

```bash
python main.py --build --source ERIx8msj --output ERIx8msj_managed --profile mapping
```

Note: POE 2 online filters may be plain text files without a file extension.

Available profiles:

- mapping
- crafting
- league_start

## Notes

This project is intentionally scoped to a legal, non-cheat helper for personal use and progression support.
