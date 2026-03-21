# PlaneLogistics

A SWISS International Air Lines intelligence platform that combines real-time ADS-B flight tracking with financial modeling, ML predictions, and scenario analysis — all from publicly available data.

## What It Does

**Live Operations** — Tracks all SWISS International Air Lines flights worldwide via OpenSky Network ADS-B data, enriched with aircraft type and fuel burn estimates (OpenAP), displayed on a real-time global Leaflet map.

**SWISS KPI Analytics** — Computes airline-analyst-grade metrics from tracked SWISS flights: Available Seat Kilometers, fleet utilization, route frequency, turnaround time, and fuel efficiency.

**Financial Intelligence** — Pulls jet fuel prices (EIA), carbon credit prices (EU ETS), and exchange rates (ECB), then estimates SWISS's Cost per ASK (CASK) and Revenue per ASK (RASK) broken down by component.

**ML Predictions** — Trains models on accumulated data to identify what drives costs (feature importance), forecast CASK trends, score route profitability, and flag fuel burn anomalies.

**Scenario Engine** — "What if fuel prices rise 20%?", "What if SWISS adds ZRH-BKK?", "What if the CHF strengthens?" — runs what-if analysis against the latest baseline and shows the impact on CASK/RASK spread.

## Pages

| Page | URL | What You'll See |
|------|-----|-----------------|
| **Live Map** | `/dashboard` | All SWISS flights worldwide on a Leaflet map, click for details (altitude, speed, fuel rate, CO2) |
| **KPIs** | `/analytics` | SWISS operational metrics: ASK, fleet utilization, departures, turnaround time, with trend charts and fleet table |
| **Economics** | `/economics` | Economic indicator cards (fuel, carbon, FX), CASK breakdown pie chart, CASK vs RASK trend, stacked cost components |
| **ML & Predictions** | `/predictions` | Feature importance bars, CASK forecast with confidence bands, fuel anomaly table, route profitability scores |
| **Scenarios** | `/scenarios` | 8 preset what-if scenarios, custom parameter builder, delta charts, scenario history |
| **Schedule** | `/schedule` | Learned flight schedule patterns, weekly heatmap, imputed flights with status tracking |

## Quick Start

```bash
# 1. Clone and configure
cp .env.example .env
# Edit .env: add OPENSKY_CLIENT_ID and OPENSKY_CLIENT_SECRET
# Add EIA_API_KEY for jet fuel & crude oil prices (free at https://www.eia.gov/opendata/register.php)

# 2. Start everything (first time — builds production frontend)
docker compose up --build

# 3. Open
open http://localhost:3000

# Subsequent starts (no rebuild needed unless code changes)
docker compose up
```

The dashboard starts showing live flights within ~30 seconds. KPIs and economics populate over time as data accumulates (KPIs compute hourly, economic data fetches every 6 hours).

## Running Without Docker

```bash
# Terminal 1: Infrastructure
docker compose up postgres redis

# Terminal 2: Backend
cd backend
pip install -r requirements.txt
uvicorn main:app --reload    # http://localhost:8000

# Terminal 3: Frontend
cd frontend
npm install
npm run dev                  # http://localhost:3000
```

## API

All endpoints return `{ data, error, meta }`. Interactive docs at `http://localhost:8000/docs`.

| Prefix | Endpoints |
|--------|-----------|
| `/flights` | `/live`, `/history` |
| `/analytics` | `/fuel`, `/emissions`, `/network`, `/route-performance`, `/flight-deviations`, `POST /route-performance/compute` |
| `/kpi` | `/current`, `/history`, `/fleet`, `/routes`, `POST /compute` |
| `/economics` | `/latest`, `/history/{factor}`, `/unit-economics/current`, `/cask-breakdown`, `POST /refresh` |
| `/predictions` | `/feature-importance`, `/forecasts`, `/anomalies`, `/route-profitability`, `POST /train` |
| `/scenarios` | `POST /`, `GET /`, `GET /{id}`, `DELETE /{id}`, `/presets/list` |
| `/schedule` | `/patterns`, `/imputed`, `POST /run` |
| `/ws/flights` | WebSocket — real-time flight updates |

## Project Structure

```
PlaneLogistics/
├── backend/                   FastAPI (Python 3.11, async)
│   ├── services/              Core business logic
│   │   ├── opensky.py         ADS-B data ingestion
│   │   ├── fuel_model.py      OpenAP fuel/CO2 estimation
│   │   ├── kpi_aggregator.py  SWISS operational KPIs
│   │   ├── economic_etl.py    External data pipeline (ECB, EIA, carbon)
│   │   ├── unit_economics.py  CASK/RASK modeling
│   │   ├── ml_pipeline.py     ML models (sklearn, LightGBM)
│   │   └── scenario_engine.py What-if analysis
│   ├── api/routes/            REST endpoints
│   └── models/                Pydantic data models
├── frontend/                  Next.js 14 (App Router, TypeScript)
│   └── src/app/               Pages: dashboard, analytics, economics, predictions, scenarios, schedule
├── db/init.sql                TimescaleDB schema (10 tables)
├── docker-compose.yml         Postgres + TimescaleDB, Redis, backend, frontend
└── docs/ARCHITECTURE.md       Detailed system architecture
```

## Tech Stack

- **Backend:** FastAPI, SQLAlchemy (async), APScheduler, OpenAP, scikit-learn, LightGBM
- **Frontend:** Next.js 14, React 18, Leaflet, Recharts
- **Data:** TimescaleDB (PostgreSQL), Redis
- **Sources:** OpenSky Network (ADS-B), ECB (FX rates), EIA (fuel prices), Ember (carbon prices)

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `OPENSKY_CLIENT_ID` | Yes | OpenSky OAuth2 client ID |
| `OPENSKY_CLIENT_SECRET` | Yes | OpenSky OAuth2 client secret |
| `EIA_API_KEY` | Recommended | EIA API key for jet fuel & Brent crude prices ([register free](https://www.eia.gov/opendata/register.php)) |
| `AIRLABS_API_KEY` | Optional | AirLabs API key for full SWISS route database ([register free](https://airlabs.co)). Without it, routes are learned automatically from flight data |
| `COLLECT_MODE` | Optional | Set to `true` for lightweight data collection mode (see below) |
| `DATABASE_URL` | Auto | PostgreSQL connection string |
| `REDIS_URL` | Auto | Redis connection string |

## Collect Mode

For long-running data collection with minimal resource usage — no frontend, no heavy compute, just poll and store.

```bash
# In .env, set:
COLLECT_MODE=true

# Prevent sleep while keeping display off (runs until you Ctrl+C)
  caffeinate -s docker compose up postgres backend

  caffeinate -s tells macOS to stay awake even with the lid closed (when plugged in). The display will still turn off to save power, but the
  process keeps running.

# Only need Postgres + backend (no frontend, no Redis required):
docker compose up postgres backend
```

**What changes in collect mode:**

| Component | Full mode | Collect mode |
|-----------|-----------|--------------|
| OpenSky poll | Every 30s | Every 60s |
| Enrichment + Postgres write | Yes | Yes |
| Route learning | Yes | Yes |
| Flight aggregation | Every 5 min | Every 5 min |
| Redis cache / WebSocket | Yes | Skipped |
| KPI computation | Hourly | Skipped |
| Route performance | Hourly | Skipped |
| Unit economics | Hourly | Skipped |
| Economic ETL | Every 6 hrs | Skipped |
| Frontend | Running | Not started |

This is useful for collecting flight data over days/weeks on a laptop without draining resources. When you want to analyze the data, switch back to `COLLECT_MODE=false` and run `docker compose up` — all collected data is there, and the KPI/economics jobs will compute from it.
