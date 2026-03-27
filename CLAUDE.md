# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**FreightFlow** is a US freight supply chain intelligence platform. It lets users pick a finished product (e.g., Motor Vehicles), select an assembly location, and visualize how precursor raw materials (steel, plastics, electronics, chemicals) flow across America's freight network to reach that destination — with cost modeling, mode analysis, and Sankey-like weighted flow lines on an interactive map.

Built on FAF5 (Freight Analysis Framework v5) data from BTS/FHWA, with cost estimates grounded in ATRI/AAR/BTS benchmark rates.

**Purpose:** Portfolio piece for job applications.

## Commands

```bash
# First-time setup
cp .env.example .env          # optionally add EIA_API_KEY for diesel/crude prices

# Start all services
docker compose up             # postgres, redis, backend, frontend

# Individual services
docker compose up backend     # FastAPI on :8000
docker compose up frontend    # Next.js on :3000
docker compose up postgres redis  # infra only

# Backend dev (outside Docker)
cd backend && pip install -r requirements.txt
uvicorn main:app --reload

# Frontend dev (outside Docker)
cd frontend && npm install && npm run dev

# Backend tests
cd backend && python3 -m pytest tests/ -v

# View API docs
open http://localhost:8000/docs
```

## Architecture

```
frontend/          Next.js 14 (App Router, TypeScript)
backend/           FastAPI (Python 3.11, async)
db/init.sql        PostgreSQL schema (runs once on container init)
docker-compose.yml postgres, redis, backend, frontend
```

### Request / data flow

```
Browser  →  REST /supply-chain/* →  backend/api/routes/supply_chain.py → Postgres + cost model
Browser  →  REST /flows/*        →  backend/api/routes/flows.py → Postgres
Browser  →  REST /economics/*    →  backend/api/routes/economics.py → Postgres
Browser  →  REST /tracking/*     →  backend/api/routes/tracking.py → Postgres + cost model

APScheduler (lifespan):
  Every 6hrs  →  services/economic_etl.py → Postgres (economic_factors)

Startup:
  seed_zones() + seed_commodities() + seed_corridors() → Postgres (reference data)
  load_faf5_data() → Postgres (freight_flows from CSVs)
```

### Key backend files

| File | Purpose |
|------|---------|
| `backend/main.py` | FastAPI app, CORS, lifespan (seed data + scheduler) |
| `backend/config.py` | Settings via `pydantic-settings`; reads `.env` |
| `backend/services/commodity_dependencies.py` | Finished goods → precursor material mappings (6 products, BOM ratios) |
| `backend/api/routes/supply_chain.py` | Supply chain analysis: finished goods list, assembly zones, precursor flow analysis |
| `backend/services/faf5_loader.py` | FAF5 CSV ETL: parse, unpivot year columns, batch insert |
| `backend/services/faf5_zones.py` | Zone centroids, mode codes, commodity codes |
| `backend/services/corridor_definitions.py` | Seed 3 corridors + zones + commodities |
| `backend/services/freight_cost_model.py` | Cost per ton-mile by mode, diesel sensitivity, cost estimation |
| `backend/services/freight_unit_economics.py` | Cost breakdown per ton-mile (fuel/labor/equipment/insurance/tolls) |
| `backend/services/economic_etl.py` | External data: EIA diesel/crude, FRED freight TSI |
| `backend/api/websocket.py` | Connection registry + `broadcast()` helper |
| `backend/api/routes/tracking.py` | Commodity list endpoint |
| `backend/db/session.py` | Async SQLAlchemy engine + `get_db()` dependency |

### Key frontend files

| File | Purpose |
|------|---------|
| `frontend/src/app/page.tsx` | Landing page with hero and single CTA |
| `frontend/src/app/explorer/page.tsx` | Supply Chain Explorer: selectors, map, precursor cards, cost charts |
| `frontend/src/components/Map/SupplyChainMap.tsx` | Leaflet map with weighted precursor flow lines (fan-in visualization) |
| `frontend/src/components/Navigation/NavBar.tsx` | Top navigation bar |
| `frontend/src/components/Navigation/LayoutShell.tsx` | Conditional NavBar (hidden on landing) |
| `frontend/src/hooks/useLeafletMap.ts` | Shared Leaflet map initialization hook |
| `frontend/src/lib/api.ts` | Typed REST helpers for all endpoints |
| `frontend/src/types/index.ts` | All TypeScript interfaces |

### Database schema (db/init.sql)

| Table | Purpose |
|-------|---------|
| `faf_zones` | 132 FAF zone reference data (id, name, state, lat/lon centroid) |
| `commodities` | 43 SCTG commodity codes + names |
| `freight_flows` | Core FAF5 data: origin, dest, commodity, mode, year, tons, value, ton-miles |
| `corridors` | 3 curated corridor definitions with zone arrays |
| `freight_rates` | Cost per ton-mile by mode and year |
| `freight_unit_economics` | Cost breakdown per ton-mile (fuel, labor, equipment, insurance, tolls) |
| `economic_factors` | Date-indexed time series (diesel price, crude, freight TSI) |

## API conventions

All endpoints return `{ data, error, meta }`.

Optional: `EIA_API_KEY` for diesel / crude oil prices (free at eia.gov).

## Mandatory documentation rules

When adding, removing, or changing any environment variable (in `config.py`, `.env.example`, or `.env`):
1. Update the **Environment Variables** table in `README.md`
2. Update `.env.example` with the new variable and a comment explaining it

When adding a new backend service file, add it to the **Key backend files** table above.

When adding, changing, or removing any hardcoded estimation constant (default values, thresholds, conversion factors, benchmark percentages, etc.):
1. Update `docs/ESTIMATION_CONSTANTS.md` with the value, file location, and rationale
2. If the value came from a specific source, cite it in the rationale
