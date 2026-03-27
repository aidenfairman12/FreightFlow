# FreightFlow — System Architecture

## High-Level Overview

```
┌─────────────────────────────────────────────────────────────┐
│                      Browser (Next.js)                       │
│                                                              │
│     /                 /explorer                              │
│     Landing Page      Supply Chain Explorer                  │
└─────────────────────────┬────────────────────────────────────┘
                          │ REST
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                    FastAPI Backend (:8000)                    │
│                                                              │
│  /supply-chain/*  /flows/*  /economics/*  /tracking/*        │
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
    │  (cache)   │    │            │    │                  │
    └────────────┘    └────────────┘    └─────────────────┘
```

## Data Pipeline

### 1. Startup — Reference Data Seeding

```
corridor_definitions.py  →  seed_zones()        132 FAF zone centroids
                         →  seed_commodities()   43 SCTG commodity codes
                         →  seed_corridors()     3 curated corridors
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
/supply-chain/analyze     →  commodity_dependencies.py + freight_cost_model.py
                          →  Query freight_flows per precursor → aggregate → cost estimate
```

## Database Schema

```
PostgreSQL
├── faf_zones              132 FAF zone reference data (id, name, state, lat/lon)
├── commodities            43 SCTG commodity codes + names
├── freight_flows          Core FAF5 data (origin, dest, commodity, mode, year, tons, value, ton-miles)
├── corridors              3 curated corridor definitions with zone arrays
├── freight_rates          Cost per ton-mile by mode and year
├── freight_unit_economics Cost breakdown per ton-mile (fuel/labor/equipment/insurance/tolls)
└── economic_factors       Time-series economic data (diesel, crude, freight TSI)
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
│   └── economics.py               Economic factors + snapshot
├── services/                      Business logic
│   ├── commodity_dependencies.py  Finished goods → precursor material mappings
│   ├── faf5_loader.py             FAF5 CSV ETL (parse, unpivot, batch insert)
│   ├── faf5_zones.py              Zone centroids, mode codes, commodity codes
│   ├── corridor_definitions.py    Seed corridors + zones + commodities
│   ├── freight_cost_model.py      Cost per ton-mile by mode, diesel sensitivity
│   ├── freight_unit_economics.py  Cost breakdown per ton-mile
│   └── economic_etl.py            EIA diesel/crude, FRED freight TSI
└── api/
    ├── websocket.py               WebSocket connection registry + broadcast
    └── routes/
        ├── supply_chain.py        GET /finished-goods, /assembly-zones, /analyze
        ├── flows.py               GET /flows/, /top-corridors, /mode-trends, /zones
        ├── economics.py           GET /economics/latest, /history, /cost-breakdown
        └── tracking.py            GET /tracking/commodities
```

## Frontend Page Map

```
frontend/src/
├── app/
│   ├── layout.tsx                 Root layout with LayoutShell
│   ├── page.tsx                   Landing page (hero + single CTA)
│   └── explorer/page.tsx          Supply Chain Explorer
├── components/
│   ├── Map/SupplyChainMap.tsx     Leaflet map (precursor flow fan-in, weighted lines)
│   └── Navigation/
│       ├── NavBar.tsx             Top navigation bar
│       └── LayoutShell.tsx        Conditional NavBar (hidden on landing)
├── hooks/
│   └── useLeafletMap.ts           Shared Leaflet initialization hook
├── lib/
│   ├── api.ts                     Typed REST helpers
│   └── chart-theme.ts            Recharts styling constants
└── types/
    └── index.ts                   All TypeScript interfaces
```

## Key Design Decisions

- **FAF5 as foundation**: Free, public, rich multi-modal data (2012-2022 + projections to 2055)
- **Supply chain story**: Instead of raw data tables, trace precursor materials to finished goods — shows domain knowledge
- **Sankey-like map**: Flow line thickness = tonnage, color = precursor commodity — visually striking
- **Cost model from benchmarks**: ATRI/AAR/BTS published rates, not proprietary data
- **Diesel price sensitivity**: Fuel cost share differs by mode (truck 38%, rail 18%)
- **6 curated finished goods**: Enough variety to demonstrate the concept without overwhelming
- **Filtered assembly zones**: Only show zones with actual inbound data, not all 132
