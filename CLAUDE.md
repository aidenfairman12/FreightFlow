# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**PlaneLogistics** is a Swiss Airspace Real-Time Logistics Analytics Platform. It ingests live ADS-B flight data from OpenSky Network, enriches it with aircraft performance data (OpenAP), and serves a Next.js dashboard with fuel efficiency, CO2 emissions, network analysis, and capacity utilization analytics.

The project is currently in **Phase 0 → Phase 1** (data pipeline + live map). `files/swiss-airspace-poc.jsx` is the reference PoC dashboard. `files/swiss-airspace-architecture.md` is the full architecture plan.

## Commands

```bash
# First-time setup
cp .env.example .env          # fill in OpenSky credentials

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

APScheduler (lifespan)  →  services/opensky.py  →  Redis (live cache)
                                                 →  Postgres state_vectors (history)
                        →  services/enrichment.py (aircraft type, airline)
                        →  services/fuel_model.py (OpenAP)
```

### Key backend files

| File | Purpose |
|------|---------|
| `backend/main.py` | FastAPI app, CORS, lifespan (scheduler hookup point) |
| `backend/config.py` | All settings via `pydantic-settings`; reads `.env` |
| `backend/services/opensky.py` | OAuth2 token + Swiss bounding box poll |
| `backend/services/fuel_model.py` | OpenAP wrapper; lazy-loads per aircraft type |
| `backend/services/enrichment.py` | ICAO24 → aircraft type, callsign → airline |
| `backend/api/websocket.py` | Connection registry + `broadcast()` helper |
| `backend/db/session.py` | Async SQLAlchemy engine + `get_db()` dependency |

### Key frontend files

| File | Purpose |
|------|---------|
| `frontend/src/app/dashboard/page.tsx` | Main dashboard layout; owns selected-flight state |
| `frontend/src/components/Map/FlightMap.tsx` | Leaflet map (client-only, SSR disabled) |
| `frontend/src/lib/api.ts` | Typed REST helpers using `NEXT_PUBLIC_API_URL` |
| `frontend/src/lib/websocket.ts` | `createFlightSocket()` WebSocket factory |
| `frontend/src/types/index.ts` | `StateVector`, `EnrichedFlight`, `ApiResponse<T>` |

### Database schema (db/init.sql)

- **`state_vectors`** — TimescaleDB hypertable; one row per poll per aircraft
- **`flights`** — Enriched completed flights (origin, destination, fuel, CO2)
- **`aircraft_registry`** — ICAO24 → aircraft type cache
- **`route_analytics`** — Aggregated route frequency and fuel averages

## API conventions

All endpoints return `{ data, error, meta }`.

OpenSky credentials: `OPENSKY_CLIENT_ID` + `OPENSKY_CLIENT_SECRET` (OAuth2 client credentials, not username/password — the old auth was deprecated March 2026).

## Phase roadmap

1. **Phase 1 (Weeks 1–4):** Wire APScheduler → `opensky.py` → Redis → WebSocket → live map markers
2. **Phase 2 (Weeks 5–8):** Fuel modeling, route detection, network analytics, TimescaleDB storage
3. **Phase 3 (Weeks 9–12):** Historical replay, weather (METAR), temporal patterns
4. **Phase 4 (Weeks 13–20):** ML — delay prediction, fuel optimization, anomaly detection
