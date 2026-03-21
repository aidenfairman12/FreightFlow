# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**PlaneLogistics** is a SWISS Airline Intelligence Platform. It tracks all SWISS International Air Lines (SWR) and Edelweiss Air (EDW) flights worldwide via OpenSky ADS-B data and layers on financial modeling, ML predictions, and scenario analysis — all from publicly available data. The ingestion pipeline fetches global state vectors and filters to SWR + EDW callsigns, so only SWISS/Edelweiss flights are stored and displayed. Edelweiss is a SWISS subsidiary and is counted as part of the SWISS (LX) fleet in Lufthansa Group reporting.

Phases 1-2 (live ADS-B + fuel modeling) and Phases 5-9 (SWISS BI platform) are complete. `files/swiss-airspace-poc.jsx` is the original PoC. `files/swiss-airspace-architecture.md` is the original architecture plan.

## Commands

```bash
# First-time setup
cp .env.example .env          # fill in OpenSky credentials + optional EIA_API_KEY

# Start all services
docker compose up             # postgres + timescaledb, redis, backend, frontend

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
docker compose exec backend pytest
# or locally: cd backend && pytest

# View API docs
open http://localhost:8000/docs
```

## Architecture

```
frontend/          Next.js 14 (App Router, TypeScript)
backend/           FastAPI (Python 3.11, async)
db/init.sql        TimescaleDB schema (runs once on postgres container init)
docker-compose.yml postgres + timescaledb, redis, backend, frontend
```

### Request / data flow

```
Browser  →  WebSocket /ws/flights  →  backend/api/websocket.py  →  broadcast()
Browser  →  REST /flights/live     →  backend/api/routes/flights.py  → Redis
Browser  →  REST /analytics/*      →  backend/api/routes/analytics.py → Postgres
Browser  →  REST /kpi/*            →  backend/api/routes/kpi.py → Postgres
Browser  →  REST /economics/*      →  backend/api/routes/economics.py → Postgres
Browser  →  REST /predictions/*    →  backend/api/routes/predictions.py → Postgres + ML
Browser  →  REST /scenarios/*      →  backend/api/routes/scenarios.py → Postgres
Browser  →  REST /schedule/*       →  backend/api/routes/schedule.py → Postgres

APScheduler (lifespan):
  Every 30s   →  services/opensky.py  →  Redis + Postgres + WebSocket
  Every 5min  →  services/flight_aggregator.py → Postgres (flights table)
  Every 1hr   →  services/schedule_imputation.py → Postgres (learn + reconcile)
  Every 1hr   →  services/kpi_aggregator.py + unit_economics.py → Postgres
  Every 1hr   →  services/route_performance.py → Postgres (route baselines + deviations)
  Every 6hrs  →  services/economic_etl.py → Postgres (economic_factors)
```

### Key backend files

| File | Purpose |
|------|---------|
| `backend/main.py` | FastAPI app, CORS, lifespan (all scheduled jobs) |
| `backend/config.py` | Settings via `pydantic-settings`; reads `.env` |
| `backend/services/opensky.py` | Global poll filtered to SWR flights |
| `backend/services/opensky_auth.py` | Shared OAuth2 token manager (cached, auto-refresh) |
| `backend/services/opensky_credits.py` | Daily API credit tracker (4000/day limit) |
| `backend/services/fuel_model.py` | OpenAP wrapper; lazy-loads per aircraft type |
| `backend/services/enrichment.py` | ICAO24 → aircraft type, callsign → airline |
| `backend/services/swiss_routes.py` | SWISS route database: seed table + self-learning persistent cache |
| `backend/services/route_cache.py` | Route cache: uses swiss_routes + OpenSky flights API for learning |
| `backend/services/swiss_filter.py` | SWISS flight identification (SWR prefix) |
| `backend/services/aircraft_data.py` | Static aircraft specs (seat counts, MTOW, range) |
| `backend/services/flight_aggregator.py` | state_vectors → flights table aggregation |
| `backend/services/kpi_aggregator.py` | Phase 5: ASK, utilization, route frequency, turnaround |
| `backend/services/economic_etl.py` | Phase 6: ECB rates, EIA fuel, carbon prices |
| `backend/services/unit_economics.py` | Phase 7: CASK/RASK computation |
| `backend/services/ml_pipeline.py` | Phase 8: Feature importance, forecasts, anomalies |
| `backend/services/scenario_engine.py` | Phase 9: What-if analysis engine |
| `backend/services/route_performance.py` | Route baselines vs actuals, deviation scoring, per-flight analysis |
| `backend/services/schedule_imputation.py` | Flight schedule learning, offline imputation, reconciliation |
| `backend/api/websocket.py` | Connection registry + `broadcast()` helper |
| `backend/db/session.py` | Async SQLAlchemy engine + `get_db()` dependency |

### Key frontend files

| File | Purpose |
|------|---------|
| `frontend/src/app/dashboard/page.tsx` | Live map + flight sidebar (Phase 1-2) |
| `frontend/src/app/analytics/page.tsx` | SWISS operational KPIs dashboard (Phase 5) |
| `frontend/src/app/economics/page.tsx` | Financial intelligence + CASK/RASK charts (Phase 6-7) |
| `frontend/src/app/predictions/page.tsx` | ML models + anomaly detection (Phase 8) |
| `frontend/src/app/scenarios/page.tsx` | What-if scenario engine (Phase 9) |
| `frontend/src/components/Map/FlightMap.tsx` | Leaflet map (client-only, SSR disabled) |
| `frontend/src/components/Navigation/NavBar.tsx` | Top navigation bar |
| `frontend/src/lib/api.ts` | Typed REST helpers for all endpoints |
| `frontend/src/lib/websocket.ts` | `createFlightSocket()` WebSocket factory |
| `frontend/src/types/index.ts` | All TypeScript interfaces |

### Database schema (db/init.sql)

Phase 1-2:
- **`state_vectors`** — TimescaleDB hypertable; one row per poll per SWISS aircraft (SWR flights only)
- **`flights`** — Enriched completed flights (origin, destination, fuel, CO2)
- **`aircraft_registry`** — ICAO24 → aircraft type cache
- **`route_analytics`** — Aggregated route frequency, fuel, CO2, distance averages
- **`route_performance`** — Per-route baselines vs recent actuals, deviation scores, categories

Phase 5-9:
- **`operational_kpis`** — Weekly/monthly SWISS operational metrics (ASK, utilization, etc.)
- **`economic_factors`** — Date-indexed time series (fuel price, carbon, FX rates)
- **`unit_economics`** — CASK/RASK estimates per period
- **`ml_predictions`** — Model forecasts with confidence bands
- **`ml_feature_importance`** — Feature importance scores per model
- **`scenarios`** — What-if scenario definitions and results

Schedule imputation:
- **`flight_schedule_patterns`** — Learned weekly schedule (callsign + day-of-week + typical departure time)
- **`imputed_flights`** — Expected flights generated during offline gaps (confirmed/missed on reconciliation)

## API conventions

All endpoints return `{ data, error, meta }`.

OpenSky credentials: `OPENSKY_CLIENT_ID` + `OPENSKY_CLIENT_SECRET` (OAuth2 client credentials, not username/password — the old auth was deprecated March 2026).

Optional: `EIA_API_KEY` for jet fuel / crude oil prices (free at eia.gov).

## Mandatory documentation rules

When adding, removing, or changing any environment variable (in `config.py`, `.env.example`, or `.env`):
1. Update the **Environment Variables** table in `README.md`
2. Update `.env.example` with the new variable and a comment explaining it
3. If the variable enables a major feature (like `COLLECT_MODE`), add a section to `README.md` explaining usage

When adding a new backend service file, add it to the **Key backend files** table above.

When adding, changing, or removing any hardcoded estimation constant (default values, thresholds, conversion factors, benchmark percentages, etc.):
1. Update `docs/ESTIMATION_CONSTANTS.md` with the value, file location, and rationale
2. If the value came from a specific source, cite it in the rationale

## Phase roadmap

1. **Phase 1 (COMPLETE):** Live ADS-B map with WebSocket broadcast
2. **Phase 2 (COMPLETE):** Fuel modeling, enrichment, TimescaleDB persistence
3. **Phase 3 (IN PROGRESS):** Historical replay, flight aggregation, weather
4. **Phase 4 (IN PROGRESS):** Route network analytics, basic anomaly detection
5. **Phase 5 (COMPLETE):** SWISS operational KPI pipeline (ASK, utilization, turnaround)
6. **Phase 6 (COMPLETE):** External financial data ETL (ECB, EIA, carbon)
7. **Phase 7 (COMPLETE):** Unit economics modeling (CASK/RASK estimation)
8. **Phase 8 (COMPLETE):** ML predictions (feature importance, forecasts, profitability)
9. **Phase 9 (COMPLETE):** Scenario engine (what-if analysis)
