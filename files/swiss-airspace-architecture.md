# Swiss Airspace Logistics Platform — Architecture & Project Plan

## 1. Project Vision

A real-time logistics analytics platform for Swiss airspace that goes beyond flight tracking to provide supply chain insights: network analysis, fuel efficiency modeling, capacity estimation, emissions accounting, and (in later phases) machine learning for prediction and optimization.

**What makes this different from FlightRadar:** You're building an *analytical layer* on top of raw ADS-B data. FlightRadar shows where planes are. Your platform shows what that means — in terms of fuel economics, network efficiency, capacity utilization, and environmental impact.

---

## 2. Data Sources — Deep Dive

### 2.1 Core: OpenSky Network (Real-time ADS-B)

**What it provides:** Live state vectors for every aircraft broadcasting ADS-B within OpenSky's receiver coverage. Each state vector includes ICAO24 address, callsign, origin country, longitude, latitude, barometric altitude, ground speed, heading, vertical rate, and position source.

**API details:**

- Base URL: `https://opensky-network.org/api/states/all`
- Swiss bounding box filter: `?lamin=45.8&lamax=47.9&lomin=5.9&lomax=10.6`
- Authentication: OAuth2 via API client credentials (free account required)
- Rate limits: 4,000 API credits/day for registered users, 8,000 for active contributors
- Time resolution: 5 seconds for authenticated users, 10 seconds for anonymous
- Historical data: Flight-level data available via Trino database for previous days (nightly batch)
- Python/Java bindings available; note the official bindings are moving to OAuth2 from March 2026

**Coverage in Switzerland:** Excellent — OpenSky is headquartered in Switzerland (ETH Zürich and Bern University of Applied Sciences), and the density of ADS-B receivers in Switzerland is among the highest globally.

**Key limitation:** No commercial data — no schedules, no delays, no passenger counts. Pure transponder data only.

### 2.2 Aircraft Performance: OpenAP (Open Aircraft Performance)

**What it provides:** An open-source Python library developed at TU Delft for aircraft performance modeling. Includes aircraft properties (dimensions, weight, capacity, engine type), fuel flow models for all flight phases, drag polar models, emissions calculations (CO2, NOx, SOx, soot, H2O), and kinematic models (typical speeds, climb/descent rates).

**How to use it:**

```python
import openap

# Get aircraft properties
props = openap.prop.aircraft("A320")
# props includes: max passengers, MTOW, wing area, engine type, etc.

# Estimate fuel flow
fuelflow = openap.FuelFlow("A320")
ff = fuelflow.enroute(mass=65000, tas=450, alt=35000)  # kg/s

# Estimate emissions
emission = openap.Emission("A320")
nox = emission.nox(ff, tas=450, alt=35000)  # kg/s
```

**Coverage:** Around 30+ of the most common commercial aircraft types. This covers the vast majority of traffic you'll see in Swiss airspace.

**Why this over BADA:** BADA (EUROCONTROL) is more comprehensive (250+ aircraft models) and more precise, but requires a license agreement. The model specifications and pyBADA code are open on GitHub, but the actual aircraft-specific coefficient datasets are licensed. OpenAP is fully open and sufficient for a project of this scope. You can upgrade to BADA later if you pursue academic affiliation.

### 2.3 Airport Data: OurAirports

**What it provides:** A public-domain database of 78,000+ airports worldwide, including all Swiss airports and airfields. Each entry has ICAO/IATA codes, coordinates, elevation, runway information, and frequencies.

**Format:** Downloadable CSV files, updated nightly. Hosted on GitHub at `davidmegginson/ourairports-data`.

### 2.4 Airspace Structure: openAIP

**What it provides:** Open aeronautical data including airspace boundaries (CTR, TMA, restricted areas), navaids, and airport details. Useful for showing controlled vs. uncontrolled airspace on your map.

### 2.5 Weather: Aviation Weather (METAR/TAF)

**What it provides:** METAR (current observations) and TAF (forecasts) for Swiss airports. Critical for the ML phase — wind speed/direction significantly affects fuel burn, and visibility/weather affects routing.

**Sources:**

- NOAA Aviation Weather Center: free, station-specific (e.g., LSZH.TXT for Zürich)
- AVWX-Engine: open-source weather parsing for METAR and TAF

### 2.6 Supplementary Sources

- **OpenFlights:** Airline and route databases (historical, not actively updated since 2014, but useful for static reference)
- **EUROCONTROL Small Emitters Tool:** Provides fuel consumption coefficients per aircraft type with a simple distance-based formula — good for quick estimates before you integrate OpenAP
- **ICAO Engine Emissions Databank:** The most comprehensive engine emissions dataset, maintained by ICAO
- **FOCA (Swiss Federal Office of Civil Aviation):** Publishes Swiss-specific aviation statistics and operational data
- **OPDI (Open Performance Data Initiative):** Enhanced OpenSky flight data with phase-of-flight segmentation (takeoff, climb, cruise, descent, landing)

---

## 3. System Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        CLIENT (React/Next.js)                       │
│  ┌──────────┐ ┌──────────────┐ ┌───────────┐ ┌──────────────────┐  │
│  │ Live Map  │ │ Flight Detail│ │ Network   │ │ Analytics/ML     │  │
│  │ (Mapbox/  │ │ Panel        │ │ Graph     │ │ Dashboard        │  │
│  │  Leaflet) │ │              │ │ Analysis  │ │                  │  │
│  └─────┬─────┘ └──────┬───────┘ └─────┬─────┘ └────────┬─────────┘  │
│        └───────────────┴───────────────┴────────────────┘            │
│                              │ WebSocket + REST                      │
└──────────────────────────────┼───────────────────────────────────────┘
                               │
┌──────────────────────────────┼───────────────────────────────────────┐
│                        API LAYER (FastAPI)                           │
│  ┌───────────────┐  ┌───────────────┐  ┌──────────────────────────┐ │
│  │ /flights/live │  │ /flights/hist │  │ /analytics/*             │ │
│  │ WebSocket     │  │ REST          │  │ /network, /fuel, /ml     │ │
│  └───────┬───────┘  └───────┬───────┘  └────────────┬─────────────┘ │
└──────────┼──────────────────┼───────────────────────┼───────────────┘
           │                  │                       │
┌──────────┼──────────────────┼───────────────────────┼───────────────┐
│          │           DATA PROCESSING LAYER          │               │
│  ┌───────▼───────┐  ┌──────▼──────┐  ┌─────────────▼─────────────┐ │
│  │ Ingestion     │  │ Enrichment  │  │ Analytics Engine          │ │
│  │ Service       │  │ Pipeline    │  │                           │ │
│  │               │  │             │  │ • Fuel burn calculator    │ │
│  │ • Poll OpenSky│  │ • Aircraft  │  │   (OpenAP integration)   │ │
│  │   every 5-10s │  │   type      │  │ • Network graph builder  │ │
│  │ • Normalize   │  │   lookup    │  │ • Capacity estimator     │ │
│  │   state       │  │ • Airline   │  │ • Emissions aggregator   │ │
│  │   vectors     │  │   mapping   │  │ • Route efficiency calc  │ │
│  │ • Detect new  │  │ • Airport   │  │                          │ │
│  │   flights &   │  │   matching  │  │ [PHASE 3: ML Models]     │ │
│  │   completions │  │ • Fuel/perf │  │ • Delay prediction       │ │
│  │               │  │   model     │  │ • Fuel optimization      │ │
│  │               │  │   binding   │  │ • Demand forecasting     │ │
│  │               │  │ • Weather   │  │ • Anomaly detection      │ │
│  └───────┬───────┘  └──────┬──────┘  └───────────────────────────┘ │
└──────────┼──────────────────┼───────────────────────────────────────┘
           │                  │
┌──────────┼──────────────────┼───────────────────────────────────────┐
│          │           DATA STORAGE LAYER                              │
│  ┌───────▼───────┐  ┌──────▼──────────────────────────────────────┐ │
│  │ Redis         │  │ PostgreSQL + TimescaleDB                    │ │
│  │               │  │                                             │ │
│  │ • Current     │  │ • flights (historical)                     │ │
│  │   state       │  │ • state_vectors (time-series)              │ │
│  │   vectors     │  │ • aircraft_registry                        │ │
│  │ • WebSocket   │  │ • airports                                 │ │
│  │   pub/sub     │  │ • route_analytics                          │ │
│  │ • Rate limit  │  │ • fuel_estimates                           │ │
│  │   tracking    │  │ • weather_observations                     │ │
│  └───────────────┘  └─────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
           │
┌──────────┼──────────────────────────────────────────────────────────┐
│          │         EXTERNAL DATA SOURCES                            │
│  ┌───────▼───────┐  ┌──────────────┐  ┌──────────┐  ┌───────────┐ │
│  │ OpenSky       │  │ OpenAP       │  │ OurAir-  │  │ NOAA/AVWX │ │
│  │ Network API   │  │ (Python lib) │  │ ports    │  │ Weather   │ │
│  └───────────────┘  └──────────────┘  └──────────┘  └───────────┘ │
└─────────────────────────────────────────────────────────────────────┘
```

### 3.1 Technology Stack (Recommended)

**Backend:**

- Python 3.11+ with FastAPI — fast async web framework, excellent for WebSocket + REST
- OpenAP library for aircraft performance and fuel modeling
- NetworkX for graph-based network analysis
- Celery or APScheduler for periodic data ingestion tasks
- Redis for caching live state vectors and pub/sub for WebSocket broadcast
- PostgreSQL with TimescaleDB extension for time-series state vector storage

**Frontend:**

- React 18+ (or Next.js for SSR if you want SEO later)
- Mapbox GL JS or Leaflet for the interactive map (Mapbox has better 3D/performance; Leaflet is fully open)
- D3.js or Recharts for analytics charts
- WebSocket client for live updates

**ML Phase (later):**

- scikit-learn for initial models (delay prediction, clustering)
- PyTorch or TensorFlow for sequence models (trajectory prediction)
- MLflow for experiment tracking

### 3.2 Key Data Models

**StateVector (live, in Redis):**

```
icao24, callsign, origin_country, latitude, longitude,
baro_altitude, velocity, heading, vertical_rate,
on_ground, last_contact, geo_altitude, squawk, spi
```

**EnrichedFlight (in PostgreSQL):**

```
flight_id, icao24, callsign, aircraft_type, aircraft_name,
airline_code, airline_name, origin_icao, destination_icao,
first_seen, last_seen, distance_km, great_circle_km,
route_efficiency, total_fuel_kg, total_co2_kg,
max_altitude, avg_speed, phase_segments[]
```

---

## 4. Phased Development Plan

### Phase 1: Data Pipeline + Live Map (Weeks 1-4)

**Goal:** Ingest OpenSky data, enrich with aircraft metadata, display on an interactive map.

- Set up OpenSky API integration with Swiss bounding box
- Build the ingestion service polling every 10 seconds
- Cross-reference ICAO24 addresses with aircraft type database
- Display live positions on a Leaflet/Mapbox map
- Show basic flight info on click (callsign, aircraft type, altitude, speed)

### Phase 2: Analytics Layer (Weeks 5-8)

**Goal:** Add fuel modeling, network analysis, and capacity metrics.

- Integrate OpenAP for fuel burn estimation per flight
- Build route detection (matching flights to origin/destination airports)
- Compute network metrics (route frequency, hub connectivity)
- Add emissions calculations
- Build the analytics dashboard panels (fuel by type, route frequency, capacity)
- Start storing historical data in TimescaleDB

### Phase 3: Historical Analysis + Weather (Weeks 9-12)

**Goal:** Enable time-series analysis and weather correlation.

- Implement historical flight data storage and replay
- Integrate METAR/TAF weather data
- Build temporal pattern analysis (daily/weekly/seasonal)
- Route efficiency analysis (actual vs. great circle distance)
- Comparative analytics (airline-to-airline, aircraft-to-aircraft)

### Phase 4: Machine Learning (Weeks 13-20)

**Goal:** Predictive and optimization models.

- Delay prediction from historical patterns + weather features
- Fuel burn optimization (compare actual trajectories against modeled optimal)
- Demand forecasting on key routes
- Anomaly detection (unusual routing, holding patterns, diversions)
- Display ML predictions and insights in the dashboard

---

## 5. Tools & Access You'll Need

### Accounts to set up now:

1. **OpenSky Network** — Create a free account at opensky-network.org. Create an API client for OAuth2 credentials. This is your primary data source.
2. **Mapbox** (if using Mapbox GL JS) — Free tier gives 50,000 map loads/month, which is generous for development.
3. **GitHub** — For version control and accessing open datasets (OurAirports, OpenAP, OpenFlights).

### Software to install:

- Python 3.11+ with pip
- Node.js 18+ and npm
- PostgreSQL (or Docker for containerized setup)
- Redis (or Docker)
- Git

### Python libraries:

```
openap          # aircraft performance modeling
fastapi         # API framework
uvicorn         # ASGI server
httpx           # async HTTP client for OpenSky API
redis           # caching and pub/sub
sqlalchemy      # ORM
psycopg2        # PostgreSQL driver
networkx        # graph analysis
pandas          # data manipulation
numpy           # numerical computing
websockets      # WebSocket support
apscheduler     # scheduled data polling
```

### Node/React libraries:

```
react, react-dom
mapbox-gl (or leaflet + react-leaflet)
recharts (or d3)
socket.io-client (or native WebSocket)
```

---

## 6. Getting Started with Claude Code

Claude Code is Anthropic's terminal-based AI coding assistant. It reads your entire codebase, makes multi-file edits, runs commands, and manages git — all through natural language.

### Installation:

The recommended method is the native installer (no Node.js dependency):

```bash
# macOS / Linux
curl -fsSL https://claude.ai/install.sh | bash

# Windows (PowerShell)
irm https://claude.ai/install.ps1 | iex

# Verify
claude --version
```

You need a Claude Pro subscription ($20/month) or higher. The native installer auto-updates in the background.

### How to use it for this project:

Once your project repo is initialized, navigate to it and run `claude`. The first thing to do is create a `CLAUDE.md` file in your project root — this tells Claude Code about your project's structure, conventions, and commands. You can bootstrap one with the `/init` command.

Here's what a CLAUDE.md might look like for this project:

```markdown
## Commands
- `docker-compose up` - Start PostgreSQL, Redis, and the backend
- `cd backend && uvicorn main:app --reload` - Start FastAPI dev server
- `cd frontend && npm run dev` - Start React dev server
- `pytest` - Run backend tests

## Architecture
- FastAPI backend in /backend
- React frontend in /frontend
- OpenSky API integration in /backend/services/opensky.py
- OpenAP fuel modeling in /backend/services/fuel_model.py
- WebSocket for live flight updates

## Conventions
- Python: type hints, async/await for I/O
- React: functional components with hooks
- All API responses follow {data, error, meta} envelope
```

### Practical Claude Code workflow for this project:

**Scaffolding:** "Create the project structure with a FastAPI backend and React frontend. Set up Docker Compose for PostgreSQL and Redis."

**Feature building:** "Implement the OpenSky API client in backend/services/opensky.py. It should poll the Swiss bounding box every 10 seconds using OAuth2 authentication, parse state vectors, and store them in Redis."

**Debugging:** "The WebSocket connection is dropping after 30 seconds. Look at the connection handler and fix the keepalive."

**Testing:** "Write tests for the fuel burn calculator. Test against known A320 fuel consumption on a 500km route."

**Iteration:** "Refactor the flight enrichment pipeline to process aircraft lookups in parallel using asyncio.gather."

Claude Code is especially powerful for this project because it can work across backend Python and frontend React simultaneously, understand the data flow end-to-end, and help you integrate unfamiliar libraries like OpenAP.

---

## 7. Quick-Start: First 48 Hours

1. **Create OpenSky account** and generate API client credentials
2. **Set up the project repo** with the folder structure above
3. **Write a standalone Python script** that hits the OpenSky API with the Swiss bounding box and prints state vectors — verify you're getting data
4. **Install OpenAP** (`pip install openap`) and run `openap.prop.aircraft("A320")` to verify you can access aircraft data
5. **Spin up the PoC visualization** (included with this document) to see what the end-state dashboard could look like
6. **Start Claude Code** in the project directory and ask it to help you build the ingestion service
