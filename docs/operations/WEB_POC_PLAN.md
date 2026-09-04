# Web POC Plan

## Goal

Build a first usable web layer for POE Helper so market data can be viewed while playing without remembering CLI commands.

The target stack for the proof of concept is:

- Python backend with FastAPI
- TypeScript frontend with Vue
- Existing Python market logic kept as the source of truth
- Local-first operation against the current SQLite-backed data flow

## What This Is For

- a navigable dashboard instead of command memorization
- market overview, recommendation browsing, and trend inspection
- settings and holdings management from a UI
- keeping the market engine and UI loosely coupled

## What This Is Not For

- replacing the CLI immediately
- reworking the market logic before the UI boundary exists
- adding auth, multi-user support, or cloud deployment in the first pass
- changing the current fetch/scoring behavior unless the UI needs a contract adjustment

## Architecture Shape

### Core

- market fetch, normalization, scoring, recommendation generation
- SQLite persistence and historical reads
- shared response/view models

### Backend Adapter Layer

- FastAPI routes
- request validation
- view-model shaping for the frontend
- background worker endpoints and health checks

### Frontend Layer

- Vue pages and navigation
- dashboard and detail views
- settings forms
- operator-friendly filtering and table browsing

### Data Boundaries

- UI never reads SQLite directly
- UI never calls poe.ninja directly
- worker code never depends on frontend code
- both CLI and web API should consume the same application services where possible

## Step 0: Preparation

Do this first so the later work can run in parallel:

1. Freeze the contract shapes for the first web slice.
2. Decide the first pages and API endpoints.
3. Create the folder split for backend, frontend, and shared contracts.
4. Keep the CLI working as the fallback while the web layer is added.

Suggested contract set for the first slice:

- current market snapshot
- recommendation list
- item detail trend data
- holdings payload
- settings payload
- worker health/status

## Step 1: Parallelizable Work Streams

Once the contracts are fixed, the rest can move in parallel.

### Work Stream A: Backend API

- expose read-only endpoints for snapshot, recommendations, history, and health
- add settings and holdings endpoints if needed for the first UI pass
- reuse existing application services instead of duplicating logic

### Work Stream B: Frontend Shell

- create the Vue app shell and routing
- build a dashboard page with current league and latest market state
- build a recommendation page with filters and tables

### Work Stream C: Background Worker

- define a small worker entry point for market refresh
- support on-demand refresh first, then scheduled refresh later
- surface last-run and last-success metadata for the UI

### Work Stream D: Shared Models and Docs

- extract or formalize the view models needed by API and UI
- document the endpoint contracts
- keep the CLI docs aligned with the new web entry point

## First POC Pages

1. Dashboard
2. Recommendations
3. Item detail / trend view
4. Holdings
5. Settings
6. Health / status

## First POC Endpoints

- `GET /api/health`
- `GET /api/market/types`
- `GET /api/market/latest`
- `GET /api/market/history/{item_id}`
- `POST /api/market/refresh`
- `GET /api/recommendations`
- `GET /api/holdings`
- `POST /api/holdings`
- `GET /api/settings`
- `POST /api/settings`

## Suggested Repo Split

- `app/domain/` for rules and core types
- `app/application/` for use cases and orchestration
- `app/infrastructure/` for storage and external adapters
- `app/web/` for FastAPI and web-facing response mapping
- `web/` or `frontend/` for the Vue app
- `docs/operations/` for roadmap and handoff material

## Early Milestone Order

1. Add the backend read API.
2. Add the Vue shell and dashboard route.
3. Wire recommendations and history views.
4. Add holdings and settings editing.
5. Add the background worker and refresh status.

## How To Use With End-Of-Day Handoffs

At the end of a session, put the current checkpoint in the handoff notes and keep this file as the long-lived plan reference.

Recommended command:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/eod_handoff.ps1 -Notes "Progress update, blockers, next milestone, and link to docs/operations/WEB_POC_PLAN.md"
```

The handoff file can stay short because this plan file holds the durable structure.

## Update Rule

- Update this file when the target architecture changes.
- Update it when the first POC pages or endpoints change.
- Keep it as the single source of truth for the web prototype plan.