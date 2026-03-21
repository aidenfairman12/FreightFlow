# PlaneLogistics — System Architecture

## High-Level Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                          Browser (Next.js)                          │
│                                                                     │
│  /dashboard   /analytics   /economics   /predictions   /scenarios   │
│  Live Map     SWISS KPIs   CASK/RASK    ML Models      What-If     │
└──────┬──────────┬────────────┬────────────┬──────────────┬──────────┘
       │ WS       │ REST       │ REST       │ REST         │ REST
       ▼          ▼            ▼            ▼              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                       FastAPI Backend (:8000)                        │
│                                                                     │
│  /ws/flights   /flights/*   /analytics/*   /kpi/*   /economics/*    │
│                /predictions/*   /scenarios/*                         │
│                                                                     │
│  ┌───────────────── APScheduler (lifespan) ──────────────────┐     │
│  │  10s: OpenSky poll → enrich → Redis + Postgres + WS       │     │
│  │  5m:  Flight aggregation (state_vectors → flights)         │     │
│  │  1h:  SWISS KPI computation + unit economics               │     │
│  │  6h:  Economic ETL (ECB, EIA, carbon prices)               │     │
│  └────────────────────────────────────────────────────────────┘     │
└──────────┬─────────────────┬─────────────────┬─────────────────────┘
           │                 │                 │
           ▼                 ▼                 ▼
    ┌────────────┐   ┌────────────┐   ┌────────────────────┐
    │   Redis    │   │ TimescaleDB│   │  External APIs     │
    │  :6379     │   │  :5432     │   │  OpenSky, ECB,     │
    │ live cache │   │ 10 tables  │   │  EIA, Ember        │
    └────────────┘   └────────────┘   └────────────────────┘
```

## Data Pipeline

### 1. Ingestion (every 10 seconds)

```
OpenSky API  →  fetch_swiss_states()     Swiss bounding box ADS-B data
             →  enrichment.py            Aircraft type, airline name lookup
             →  route_cache.py           Origin/destination detection
             →  fuel_model.py            OpenAP fuel burn + CO2 estimation
             →  redis_cache.py           Store in Redis (TTL = 2×poll_interval)
             →  persistence.py           Batch INSERT into state_vectors hypertable
             →  websocket.py             Broadcast to all connected browsers
```

### 2. Flight Aggregation (every 5 minutes)

```
state_vectors  →  flight_aggregator.py   Detect aircraft that left airspace
               →  flights table          Summarize: duration, fuel, CO2, distance
```

### 3. KPI Pipeline (every hour)

```
state_vectors  →  swiss_filter.py        Filter to SWR callsign prefix
               →  kpi_aggregator.py      Compute ASK, utilization, turnaround
               →  operational_kpis       Store weekly/monthly aggregates
               →  unit_economics.py      Combine KPIs + economic factors → CASK/RASK
               →  unit_economics table   Store period estimates
```

### 4. Economic ETL (every 6 hours)

```
ECB XML feed   →  exchange rates (EUR/CHF, USD/CHF)
EIA API        →  jet fuel price, Brent crude
Ember API      →  EU ETS carbon price (EUA)
               →  economic_factors table (date-indexed time series)
```

### 5. ML Pipeline (on-demand)

```
operational_kpis + economic_factors + unit_economics
    →  ml_pipeline.py
        →  RandomForest feature importance
        →  Linear time series forecast with confidence bands
        →  GradientBoosting cost regression
        →  Route profitability scoring
        →  Z-score fuel anomaly detection
    →  ml_predictions + ml_feature_importance tables
```

## Database Schema

```
TimescaleDB
├── state_vectors (hypertable)     Raw ADS-B telemetry, one row per aircraft per poll
├── flights                        Completed flight summaries
├── aircraft_registry              ICAO24 → aircraft type cache
├── route_analytics                Aggregated route frequency + fuel averages
├── operational_kpis               Weekly/monthly SWISS metrics (ASK, utilization, etc.)
├── economic_factors               Time-series economic data (fuel, carbon, FX)
├── unit_economics                 CASK/RASK estimates per period
├── ml_predictions                 Model forecasts with confidence intervals
├── ml_feature_importance          Feature importance scores per model
└── scenarios                      What-if scenario definitions + results
```

## Backend Service Map

```
backend/
├── main.py                        App + scheduler + route registration
├── config.py                      Pydantic settings from .env
├── db/
│   └── session.py                 Async SQLAlchemy engine
├── models/                        Pydantic data models
│   ├── state_vector.py            Live flight state
│   ├── flight.py                  Completed flight
│   ├── kpi.py                     Operational KPI
│   ├── economics.py               Economic factors
│   ├── prediction.py              ML prediction
│   └── scenario.py                Scenario definition + results
├── services/                      Business logic
│   ├── opensky.py                 OpenSky OAuth2 + Swiss airspace poll
│   ├── enrichment.py              Aircraft type + airline lookup
│   ├── fuel_model.py              OpenAP fuel/CO2 estimation
│   ├── redis_cache.py             Live flight cache
│   ├── persistence.py             TimescaleDB batch inserts
│   ├── route_cache.py             Origin/destination detection
│   ├── aircraft_data.py           Static aircraft specs (30+ types)
│   ├── swiss_filter.py            SWISS flight identification
│   ├── flight_aggregator.py       state_vectors → flights
│   ├── kpi_aggregator.py          Operational KPI computation
│   ├── economic_etl.py            External data fetchers (ECB, EIA, carbon)
│   ├── unit_economics.py          CASK/RASK estimation
│   ├── ml_pipeline.py             ML model training + prediction
│   └── scenario_engine.py         What-if analysis engine
└── api/
    ├── websocket.py               WebSocket connection registry + broadcast
    └── routes/
        ├── flights.py             GET /flights/live, /flights/history
        ├── analytics.py           GET /analytics/fuel, /emissions, /network
        ├── kpi.py                 GET /kpi/current, /history, /fleet, /routes
        ├── economics.py           GET /economics/latest, /cask-breakdown, etc.
        ├── predictions.py         GET /predictions/feature-importance, /forecasts
        └── scenarios.py           POST/GET/DELETE /scenarios/*
```

## Frontend Page Map

```
frontend/src/
├── app/
│   ├── layout.tsx                 Root layout with NavBar
│   ├── page.tsx                   Redirect → /dashboard
│   ├── dashboard/page.tsx         Live Leaflet map + flight sidebar
│   ├── analytics/page.tsx         KPI cards, trend charts, fleet table
│   ├── economics/page.tsx         Economic indicators, CASK pie, CASK vs RASK
│   ├── predictions/page.tsx       Feature importance, forecasts, anomalies, routes
│   └── scenarios/page.tsx         Preset scenarios, custom builder, results
├── components/
│   ├── Map/FlightMap.tsx          Leaflet map (SSR disabled, WebSocket-driven)
│   └── Navigation/NavBar.tsx      Top navigation bar
├── lib/
│   ├── api.ts                     Typed REST helpers for all endpoints
│   └── websocket.ts               WebSocket factory
└── types/
    └── index.ts                   All TypeScript interfaces
```

## Key Design Decisions

- **TimescaleDB hypertable** for state_vectors: efficient time-range queries on high-cardinality data
- **Redis as hot cache**: live flight state with auto-expiry, decouples API reads from poll cycle
- **Fire-and-forget tasks** for enrichment: aircraft type and route lookups don't block the main poll loop
- **Semaphores (max 3)** on external API calls to avoid flooding OpenSky
- **CASK estimation from fuel proportion**: if fuel = 28% of costs (IATA benchmark), we can estimate total CASK from fuel cost alone, then break down other components
- **Walk-forward validation** for ML: time series data requires chronological splits, not random
- **SWISS-first scope**: all KPI/economics/scenarios filter to SWR callsign; Edelweiss can be added later
