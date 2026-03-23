# FreightFlow

A US multi-modal freight logistics intelligence platform that analyzes FAF5 freight flow data across major corridors with cost modeling, economic intelligence, and scenario analysis — all from publicly available BTS data.

## What It Does

**Freight Flow Map** — Visualizes 3 major US freight corridors (LA→Chicago, Houston→NYC, Seattle→Dallas) on a dark-themed Leaflet map with corridor polylines, zone markers, and a detail sidebar showing mode breakdowns and cost estimates.

**Freight Analytics** — Computes freight KPIs from FAF5 data: total tonnage, ton-miles, mode share percentages, cost per ton-mile, and value per ton. Includes commodity breakdowns, mode cost comparisons, and corridor performance scoring.

**Cost Intelligence** — Tracks diesel prices (EIA), Brent crude, trucking PPI, and freight TSI, then estimates cost per ton-mile broken down by component (fuel, labor, equipment, insurance, tolls/fees) with diesel price sensitivity.

**Scenario Engine** — "What if diesel prices rise 30%?", "What if port congestion adds 5 days?", "What if rail capacity expands 20%?" — 7 preset scenarios plus a custom 8-parameter builder showing impact on freight costs by component.

## Pages

| Page | URL | What You'll See |
|------|-----|-----------------|
| **Freight Map** | `/dashboard` | US corridor map with polylines, zone markers, corridor detail sidebar with mode breakdown |
| **Analytics** | `/analytics` | Freight KPI cards, volume/mode share trends, commodity rankings, corridor performance table |
| **Economics** | `/economics` | Economic indicator cards, cost per ton-mile pie chart, cost vs revenue trend, stacked cost components |
| **Scenarios** | `/scenarios` | 7 preset scenarios, custom 8-parameter builder, delta impact charts, scenario history |

## Quick Start

```bash
# 1. Clone and configure
cp .env.example .env
# Optionally add EIA_API_KEY for diesel & crude prices (free at https://www.eia.gov/opendata/register.php)

# 2. Download FAF5 data
# Place FAF5 CSV files in backend/data/faf5/ (see backend/data/faf5/README.md for instructions)

# 3. Start everything
docker compose up --build

# 4. Open
open http://localhost:3000
```

Corridors and reference data seed on startup. FAF5 freight flows load automatically from CSVs. KPIs compute on demand via the UI. Economic data fetches every 6 hours if `EIA_API_KEY` is set.

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

## Running Tests

```bash
cd backend
python3 -m pytest tests/ -v
```

## API

All endpoints return `{ data, error, meta }`. Interactive docs at `http://localhost:8000/docs`.

| Prefix | Endpoints |
|--------|-----------|
| `/corridors` | `GET /`, `GET /{id}/flows`, `GET /{id}/modes`, `GET /{id}/trends` |
| `/flows` | `GET /`, `GET /top-corridors`, `GET /mode-trends`, `GET /zones` |
| `/analytics` | `GET /corridor-performance`, `GET /mode-comparison`, `GET /commodity-summary`, `POST /corridor-performance/compute` |
| `/kpi` | `GET /current`, `GET /history`, `GET /mode-share`, `POST /compute` |
| `/economics` | `GET /latest`, `GET /history/{factor}`, `GET /unit-economics/current`, `GET /unit-economics/history`, `GET /cost-breakdown`, `POST /refresh` |
| `/scenarios` | `POST /`, `GET /`, `GET /{id}`, `DELETE /{id}`, `GET /presets/list` |

## Project Structure

```
FreightFlow/
├── backend/                       FastAPI (Python 3.11, async)
│   ├── main.py                    App entry point, lifespan, route registration
│   ├── config.py                  Pydantic settings from .env
│   ├── services/                  Core business logic
│   │   ├── faf5_loader.py         FAF5 CSV ETL (parse, unpivot, batch insert)
│   │   ├── faf5_zones.py          Zone centroids, mode codes, commodity codes
│   │   ├── corridor_definitions.py  Seed corridors + zones + commodities
│   │   ├── freight_cost_model.py  Cost per ton-mile by mode, diesel sensitivity
│   │   ├── freight_kpi_aggregator.py  Volume/mode/cost KPIs
│   │   ├── freight_unit_economics.py  Cost breakdown per ton-mile
│   │   ├── corridor_performance.py  Corridor scoring
│   │   ├── economic_etl.py        External data (EIA diesel/crude, FRED TSI)
│   │   └── scenario_engine.py     What-if analysis (8 parameters)
│   ├── api/routes/                REST endpoints
│   ├── models/                    Pydantic data models
│   └── tests/                     pytest test suite
├── frontend/                      Next.js 14 (App Router, TypeScript)
│   └── src/
│       ├── app/                   Pages: dashboard, analytics, economics, scenarios
│       ├── components/Map/        FreightMap (Leaflet, US corridors)
│       ├── lib/                   API client, chart theme, utilities
│       └── types/                 TypeScript interfaces
├── db/init.sql                    PostgreSQL schema (10 tables)
├── docker-compose.yml             Postgres + TimescaleDB, Redis, backend, frontend
└── docs/
    ├── ARCHITECTURE.md            System architecture diagram
    └── ESTIMATION_CONSTANTS.md    All hardcoded rates with sources
```

## Tech Stack

- **Backend:** FastAPI, SQLAlchemy (async), APScheduler, Pandas, NumPy
- **Frontend:** Next.js 14, React 18, TypeScript, Leaflet, Recharts, shadcn/ui, Tailwind CSS
- **Infrastructure:** PostgreSQL (TimescaleDB), Redis, Docker Compose
- **Data Sources:** FAF5/BTS (freight flows), EIA (diesel/crude prices), FRED (freight TSI)

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `POSTGRES_DB` | Yes | PostgreSQL database name (default: `planelogistics`) |
| `POSTGRES_USER` | Yes | PostgreSQL username (default: `planelogistics`) |
| `POSTGRES_PASSWORD` | Yes | PostgreSQL password (default: `changeme`) |
| `DATABASE_URL` | Yes | Full PostgreSQL connection string for the backend |
| `REDIS_URL` | Yes | Redis connection string (default: `redis://redis:6379`) |
| `FRONTEND_URL` | Yes | CORS origin for the frontend (default: `http://localhost:3000`) |
| `NEXT_PUBLIC_API_URL` | Yes | Backend URL for the frontend (default: `http://localhost:8000`) |
| `EIA_API_KEY` | Recommended | EIA API key for diesel & Brent crude prices ([register free](https://www.eia.gov/opendata/register.php)) |
| `FAF5_DATA_DIR` | Optional | Path to FAF5 CSVs relative to backend (default: `data/faf5`) |
| `TARGET_COMMODITY` | Optional | SCTG2 commodity code focus (default: `35` = Electronics) |

## Data Source

[FAF5 (Freight Analysis Framework v5)](https://www.bts.gov/faf) from the Bureau of Transportation Statistics — free, public freight flow data across ~132 US regions by commodity, transport mode, tonnage, and value (2012–2022 historical + projections to 2055).
