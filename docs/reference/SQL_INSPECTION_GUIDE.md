# SQLite inspection guide

This project stores market data in SQLite and is designed to be inspected locally before relying on the data pipeline.

The default database path is:

- data/market/poe_market.db

The app schema is defined in:

- app/infrastructure/market_store.py

## Tables

The store creates these tables:

- market_snapshots
- market_rows

## Typical sanity-check queries

Open the SQLite file in SQLTools or another SQLite client, then run these queries.

### 1) Check whether the database exists and contains tables

```sql
SELECT name
FROM sqlite_master
WHERE type = 'table'
ORDER BY name;
```

Expected result:

- market_snapshots
- market_rows

### 2) Check row counts

```sql
SELECT 'market_snapshots' AS table_name, COUNT(*) AS row_count FROM market_snapshots
UNION ALL
SELECT 'market_rows', COUNT(*) FROM market_rows;
```

### 3) View the latest recorded snapshots

```sql
SELECT id, league, market_type, source_file, fetched_at
FROM market_snapshots
ORDER BY fetched_at DESC
LIMIT 20;
```

### 4) View recent market rows

```sql
SELECT league, market_type, item_name, chaos_value, primary_value, vendor_value, fetched_at
FROM market_rows
ORDER BY fetched_at DESC
LIMIT 20;
```

### 5) Count rows by league and type

```sql
SELECT league, market_type, COUNT(*) AS rows
FROM market_rows
GROUP BY league, market_type
ORDER BY league, market_type;
```

### 6) Check the latest record for a specific item

```sql
SELECT *
FROM market_rows
WHERE item_name = 'Chaos Orb'
ORDER BY fetched_at DESC
LIMIT 10;
```

### 7) Check latest values for a given league and market type

```sql
SELECT item_name, chaos_value, primary_value, vendor_value, fetched_at
FROM market_rows
WHERE league = 'Runes of Aldur'
  AND market_type = 'Currency'
ORDER BY item_name
LIMIT 50;
```

### 8) Validate that item records are not duplicated unexpectedly

```sql
SELECT league, market_type, item_id, COUNT(*) AS duplicates
FROM market_rows
GROUP BY league, market_type, item_id
HAVING COUNT(*) > 1
ORDER BY duplicates DESC
LIMIT 20;
```

## Fetch type checklist

Before a live fetch is considered ready, we still need to confirm the app supports the right market fetch variants.

The relevant market fetch types are typically tracked through the CLI and the market layer, for example:

- Currency
- Fragment
- DivinationCard
- Essence
- Gem
- Map
- UniqueWeapon
- UniqueAccessory
- etc.

The exact supported types should be validated against the external API payload and app parsing logic.

### Recommended review checklist

1. Confirm which market types the external source exposes.
2. Confirm which of those types the parser accepts without dropping rows.
3. Confirm which types are safe for score generation.
4. Confirm which types should be ignored as unsupported or low-value for the current app scope.
5. Confirm the app cleansly handles missing or malformed fields for a given type.

## Recommended workflow

Use this sequence:

1. Make sure the target database file exists.
2. Run one small market fetch for a known league and type.
3. Inspect market_snapshots and market_rows in the DB.
4. Confirm the expected count, IDs, and timestamps are populated.
5. Add or refine a focused integration test based on the observed data.

This keeps the database inspection as a debugging and validation tool, while the automated tests remain the long-term regression guardrail.

## Good first validation target

A good first real fetch target is a narrow, known-good case such as:

- league: Runes of Aldur
- type: Currency

This is a minimal but realistic path to validate the storage flow before expanding to more fetch types.
