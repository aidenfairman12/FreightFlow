# FreightFlow — System Architecture

## High-Level Overview

```
┌─────────────────────────────────────────────────────────────┐
│                      Browser (Next.js)                       │
│                                                              │
│  /dashboard     /analytics     /economics     /scenarios     │
│  Freight Map    Freight KPIs   Cost Intel     What-If        │
└──────┬────────────┬──────────────┬──────────────┬───────────┘
       │ REST       │ REST         │ REST         │ REST
       ▼            ▼              ▼              ▼
┌─────────────────────────────────────────────────────────────┐
│                    FastAPI Backend (:8000)                    │
│                                                              │
│  /corridors/*  /flows/*  /analytics/*  /kpi/*                │
│  /economics/*  /scenarios/*                                  │
│                                                              │
│  ┌─────────── APScheduler (lifespan) ───────────────┐       │
│  │  Startup: seed zones + commodities + corridors    │       │
│  │  Startup: load FAF5 CSV data                      │       │
│  │  Every 6h: economic ETL (EIA diesel/crude, FRED)  │       │
│  └───────────────────────────────────────────────────┘       │
└──────────┬──────────────────┬──────────────────┬────────────┘
           │                  │                  │
           ▼                  ▼                  ▼
    ┌────────────┐    ┌────────────┐    ┌─────────────────┐
    │   Redis    │    │ PostgreSQL │    │  External APIs   │
    │  :6379     │    │  :5432     │    │  EIA, FRED       │
    │  (cache)   │    │ 10 tables  │    │                  │
    └────────────┘    └────────────┘    └─────────────────┘
```

## Data Pipeline

### 1. Startup — Reference Data Seeding

```
corridor_definitions.py  →  seed_zones()        132 FAF zone centroids
                         →  seed_commodities()   43 SCTG commodity codes
                         →  seed_corridors()     3 curated corridors (LA→Chicago, Houston→NYC, Seattle→Dallas)
```

### 2. Startup — FAF5 Data Ingestion

```
backend/data/faf5/*.csv  →  faf5_loader.py      Parse CSVs, unpivot year columns
                         →  freight_flows table  Batch INSERT with ON CONFLICT
```

### 3. Economic ETL (every 6 hours)

```
EIA API        →  diesel price (on-highway), Brent crude
FRED API       →  freight transportation services index
               →  economic_factors table (date-indexed time series)
```

### 4. On-Demand Computation

```
/kpi/compute              →  freight_kpi_aggregator.py   →  freight_kpis table
/analytics/compute        →  corridor_performance.py     →  corridor_performance table
/scenarios/ (POST)        →  scenario_engine.py          →  scenarios table
/corridors/{id}/modes     →  freight_cost_model.py       →  inline response
```

## Database Schema

```
PostgreSQL
├── faf_zones              132 FAF zone reference data (id, name, state, lat/lon)
├── commodities            43 SCTG commodity codes + names
├── freight_flows          Core FAF5 data (origin, dest, commodity, mode, year, tons, value, ton-miles)
├── corridors              3 curated corridor definitions with zone arrays
├── freight_rates          Cost per ton-mile by mode and year
├── corridor_performance   Aggregated corridor metrics per year
├── freight_kpis           Periodic aggregations (tons, mode share, cost, value)
├── freight_unit_economics Cost breakdown per ton-mile (fuel/labor/equipment/insurance/tolls)
├── economic_factors       Time-series economic data (diesel, crude, freight TSI)
└── scenarios              What-if scenario definitions + results
```

## Backend Service Map

```
backend/
├── main.py                        App + scheduler + route registration
├── config.py                      Pydantic settings from .env
├── db/
│   └── session.py                 Async SQLAlchemy engine
├── models/                        Pydantic data models
│   ├── freight.py                 Freight flows, corridors, KPIs, unit economics
│   ├── economics.py               Economic factors + snapshot
│   └── scenario.py                Scenario definition + results
├── services/                      Business logic
│   ├── faf5_loader.py             FAF5 CSV ETL (parse, unpivot, batch insert)
│   ├── faf5_zones.py              Zone centroids, mode codes, commodity codes
│   ├── corridor_definitions.py    Seed corridors + zones + commodities
│   ├── freight_cost_model.py      Cost per ton-mile by mode, diesel sensitivity
│   ├── freight_kpi_aggregator.py  Aggregate freight KPIs from flows
│   ├── freight_unit_economics.py  Cost breakdown per ton-mile
│   ├── corridor_performance.py    Corridor scoring and performance summary
│   ├── economic_etl.py            EIA diesel/crude, FRED freight TSI
│   └── scenario_engine.py         What-if analysis (8 parameters)
└── api/
    ├── websocket.py               WebSocket connection registry + broadcast
    └── routes/
        ├── corridors.py           GET /corridors/, /{id}/flows, /modes, /trends
        ├── flows.py               GET /flows/, /top-corridors, /mode-trends, /zones
        ├── analytics.py           GET /analytics/corridor-performance, /mode-comparison
        ├── kpi.py                 GET /kpi/current, /history, /mode-share
        ├── economics.py           GET /economics/latest, /history, /cost-breakdown
        └── scenarios.py           POST/GET/DELETE /scenarios/*, /presets/list
```

## Frontend Page Map

```
frontend/src/
├── app/
│   ├── layout.tsx                 Root layout with NavBar
│   ├── page.tsx                   Redirect → /dashboard
│   ├── dashboard/page.tsx         Freight corridor map + sidebar
│   ├── analytics/page.tsx         KPI cards, trends, commodity rankings
│   ├── economics/page.tsx         Economic indicators, cost breakdown charts
│   └── scenarios/page.tsx         Preset scenarios, custom builder, results
├── components/
│   ├── Map/FreightMap.tsx         US Leaflet map (corridor polylines, zone markers)
│   └── Navigation/NavBar.tsx      Top navigation bar
├── lib/
│   ├── api.ts                     Typed REST helpers for all endpoints
│   └── websocket.ts               WebSocket factory
└── types/
    └── index.ts                   All TypeScript interfaces
```

## Key Design Decisions

- **FAF5 as foundation**: Free, public, rich multi-modal data (2012-2022 + projections to 2055)
- **Cost model from benchmarks**: ATRI/AAR/BTS published rates, not proprietary data
- **Diesel price sensitivity**: Fuel cost share differs by mode (truck 38%, rail 18%), so diesel changes affect modes differently
- **Corridor-based analysis**: 3 curated corridors focus the story instead of showing 132×132 zone pairs
- **Scenario engine**: 8 parameters covering fuel, capacity, congestion, labor, demand, mode shift, carbon tax, tolls
- **Static data + economic overlay**: FAF5 is historical, but diesel/crude price feeds add a dynamic economic layer
