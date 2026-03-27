# FreightFlow

A US freight supply chain intelligence platform built on FAF5 (Freight Analysis Framework v5) data from BTS/FHWA. Analyses supply chain concentration risk and lets users simulate the disruption impact of losing any source zone for four critical US supply chains: **Automobiles, Beef, Pharmaceuticals, and Steel**.

Fully static — pre-computed from FAF5 2022 data and deployed to Vercel with no backend.

## What It Does

**Risk Overview** (`/`) — Ranks four critical US supply chains by concentration risk, showing how dependent each is on just a handful of geographic source zones. Backed by real FAF5 freight flow data for 2022.

**Supply Chain Explorer** (`/explorer`) — Pick a product, pick an assembly zone, and see weighted precursor flow lines fan into that zone from source regions across the US. Click any source zone to simulate a disruption: instant tonnage-gap and cost-impact calculation, client-side, no server needed.

## Pages

| Page | URL | What You'll See |
|------|-----|-----------------|
| **Risk Overview** | `/` | Concentration risk cards for all 4 supply chains, ranked by fragility |
| **Supply Chain Explorer** | `/explorer` | Interactive flow map, precursor breakdown, disruption simulator |

## Deploy to Vercel (free, no backend)

```bash
# 1. Push repo to GitHub
# 2. Import project on vercel.com
# 3. Set Root Directory → frontend
# 4. Deploy — done. No environment variables needed.
```

The frontend is a fully static Next.js export. All data lives in `frontend/public/data/` as pre-computed JSON files.

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

Reference data seeds on startup. FAF5 freight flows load automatically from CSVs. Economic data fetches on startup and every 6 hours if `EIA_API_KEY` is set.

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
| `/supply-chain` | `GET /finished-goods`, `GET /assembly-zones`, `GET /analyze` |
| `/flows` | `GET /`, `GET /top-corridors`, `GET /mode-trends`, `GET /zones` |
| `/economics` | `GET /latest`, `GET /history/{factor}`, `GET /cost-breakdown`, `POST /refresh` |
| `/tracking` | `GET /commodities` |

## Project Structure

```
FreightFlow/
├── backend/                       FastAPI (Python 3.11, async)
│   ├── main.py                    App entry point, lifespan, route registration
│   ├── config.py                  Pydantic settings from .env
│   ├── services/                  Core business logic
│   │   ├── commodity_dependencies.py  Finished goods → precursor mappings (6 products)
│   │   ├── faf5_loader.py         FAF5 CSV ETL (parse, unpivot, batch insert)
│   │   ├── faf5_zones.py          Zone centroids, mode codes, commodity codes
│   │   ├── corridor_definitions.py  Seed corridors + zones + commodities
│   │   ├── freight_cost_model.py  Cost per ton-mile by mode, diesel sensitivity
│   │   ├── freight_unit_economics.py  Cost breakdown per ton-mile
│   │   └── economic_etl.py        External data (EIA diesel/crude, FRED TSI)
│   ├── api/routes/                REST endpoints
│   ├── models/                    Pydantic data models
│   └── tests/                     pytest test suite
├── frontend/                      Next.js 14 (App Router, TypeScript)
│   └── src/
│       ├── app/                   Pages: landing, explorer
│       ├── components/Map/        SupplyChainMap (Leaflet, weighted flow lines)
│       ├── lib/                   API client, chart theme, utilities
│       └── types/                 TypeScript interfaces
├── db/init.sql                    PostgreSQL schema
├── docker-compose.yml             Postgres, Redis, backend, frontend
└── docs/
    ├── ARCHITECTURE.md            System architecture diagram
    ├── ESTIMATION_CONSTANTS.md    All hardcoded rates with sources
    └── ROADMAP.md                 Feature roadmap
```

## Tech Stack

- **Backend:** FastAPI, SQLAlchemy (async), APScheduler
- **Frontend:** Next.js 14, React 18, TypeScript, Leaflet, Recharts, Tailwind CSS
- **Infrastructure:** PostgreSQL, Redis, Docker Compose
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
| `FRED_API_KEY` | Optional | FRED API key for freight TSI index ([register free](https://fred.stlouisfed.org/docs/api/api_key.html)) |
| `FAF5_DATA_DIR` | Optional | Path to FAF5 CSVs relative to backend (default: `data/faf5`) |

## Data Source

[FAF5 (Freight Analysis Framework v5)](https://www.bts.gov/faf) from the Bureau of Transportation Statistics — free, public freight flow data across ~132 US regions by commodity, transport mode, tonnage, and value (2012-2022 historical + projections to 2055).
