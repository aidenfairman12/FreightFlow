# Changelog

All notable changes to PlaneLogistics are documented here.

---

## 2026-03-20 — Self-Learning Route Database (Architecture Rewrite)

**Architecture fix**: Complete rewrite of how origin/destination is resolved.

### Problem
ADS-B does not broadcast route data — only position, altitude, speed, heading, and callsign. The previous approach relied on the OpenSky flights API, which only returns completed flights (not in-progress ones), making it impossible to determine destination for airborne aircraft. Every flight showed "LSZH" as origin (hub fallback) and no destination.

### Solution: Three-tier route resolution with self-learning

1. **Learned cache** (persistent JSON) — routes discovered from completed flight data are stored permanently. Once a flight number is observed completing a route, all future flights with that callsign get instant route data. Cache persists across restarts.
2. **Static seed table** (`services/swiss_routes.py`) — ~130 known SWISS flight number → route mappings covering long-haul, European, and Geneva routes. Provides immediate coverage before the system has observed any flights.
3. **Hub fallback** — LSZH for flight numbers <2000, LSGG for 2000+.

### New files
- **`services/swiss_routes.py`**: Route database with static seed table, persistent learned cache, callsign parser, and optional AirLabs API integration.
- **`data/learned_routes.json`**: Auto-generated persistent cache of discovered routes.

### Changes
- **`services/route_cache.py`**: Rewritten to use `swiss_routes` as primary source. OpenSky flights API now feeds back into the learning system instead of being the primary lookup.
- **`services/flight_aggregator.py`**: Now populates `origin_icao` and `destination_icao` in the `flights` table.
- **`config.py`**: Added optional `AIRLABS_API_KEY` setting.
- **`main.py`**: AirLabs route bootstrap on startup (if key configured). Health endpoint now includes route database stats.

### Optional: AirLabs API integration
Set `AIRLABS_API_KEY` in `.env` (free at airlabs.co, 1000 req/month) to bulk-fetch all SWISS routes on startup. Without it, the system learns routes automatically from OpenSky data within 1-2 days of running.

---

## 2026-03-20 — Fix Origin/Destination Route Data (Token Fix)

**Bug fix**: Origin and destination airports were almost never populated in the UI.

### Root causes
1. **Token flooding** — Each route lookup and aircraft type lookup acquired its own OAuth token from OpenSky. With 50+ SWISS flights, that was ~100 token requests per poll cycle, hitting OpenSky's rate limiter and causing most lookups to fail silently.
2. **Race condition** — Route fetches are fire-and-forget background tasks. On first encounter of an aircraft, origin/destination was always `None` for the first broadcast cycle. If the background fetch failed (due to #1), it stayed `None` permanently.
3. **Wrong data for active flights** — The OpenSky flights API returns completed flight records. For a plane currently in the air, it returned the *previous leg's* route data (or null arrival airport).

### Fixes
- **Shared token manager** (`services/opensky_auth.py`): Single cached OAuth token reused across all services (state vectors, metadata, flights API). Token refreshes only when near expiry. Eliminates ~99 redundant token requests per poll cycle.
- **Callsign-based route fallback** (`services/route_cache.py`): SWISS callsigns (SWR → LX flight numbers) are decoded to determine at least the departure hub (ZRH or GVA) immediately, without any network call. This gives instant partial route data.
- **Improved route resolution**: When OpenSky flights API returns null arrival (in-flight aircraft), the callsign fallback fills in what it can. When the API fails or is rate-limited, callsign data persists instead of showing nothing.
- **`enrichment.py` and `opensky.py`** also updated to use shared token.

---

## 2026-03-20 — SWISS-Only Global Tracking

**Breaking change**: The platform now tracks only SWISS International Air Lines (SWR) flights worldwide, instead of all airlines in Swiss airspace.

### What changed
- **OpenSky ingestion** (`backend/services/opensky.py`): Removed Swiss bounding box. Now fetches global state vectors and filters server-side to `SWR` callsign prefix. Timeout increased from 15s to 30s for larger global response.
- **Analytics queries** (`backend/api/routes/analytics.py`): Added `callsign LIKE 'SWR%'` filter to fuel and emissions SQL queries.
- **Frontend map** (`frontend/src/components/Map/FlightMap.tsx`): Default view zoomed out from Switzerland (zoom 8) to Europe-wide (zoom 5, centered on Zurich). Plane icons changed from black to SWISS red (`#dc0018`).
- **Dashboard sidebar** (`frontend/src/app/dashboard/page.tsx`): Header changed to "SWISS Flight Tracker", fleet summary labeled "SWISS Fleet".
- **Flight aggregator** (`backend/services/flight_aggregator.py`): Updated docstring — no code change needed since upstream filtering means only SWISS flights reach `state_vectors`.
- **Documentation**: Updated README.md, CLAUDE.md to reflect SWISS-only global tracking.

### Why
The app's purpose is SWISS airline intelligence. Showing all airlines in Swiss airspace was a leftover from the original airspace-monitoring PoC. Tracking SWISS globally gives complete coverage of the airline's operations rather than a geographic slice of all traffic.

### Migration note
If you have existing data in `state_vectors` from before this change, it will contain non-SWISS flights. The analytics queries now filter to SWR callsigns, so old data won't affect results. No schema migration needed.

---

## 2026-03-20 — API Key Startup Validation

- Added `validate_credentials()` in `opensky.py` — tests OAuth2 token exchange at boot, disables polling if invalid.
- Added `validate_eia_key()` in `economic_etl.py` — tests EIA API key at boot, disables fuel price fetching if invalid.
- Health endpoint (`/health`) now reports `opensky` and `eia` status.

---

## 2026-03-20 — Phases 5–9 Implementation

Full SWISS airline intelligence platform built on top of the Phase 1-2 flight tracking foundation.

### Phase 5: Operational KPI Pipeline
- `services/kpi_aggregator.py` — ASK, fleet utilization, route frequency, turnaround time
- `api/routes/kpi.py` — REST endpoints for KPI data
- Frontend analytics page with KPI cards, trend charts, fleet table

### Phase 6: External Financial Data ETL
- `services/economic_etl.py` — ECB exchange rates, EIA fuel/crude prices, EU ETS carbon
- `api/routes/economics.py` — REST endpoints for economic indicators
- Frontend economics page with indicator cards, CASK breakdown, trend charts

### Phase 7: Unit Economics Modeling
- `services/unit_economics.py` — CASK/RASK estimation from public data
- CASK components: fuel, carbon, navigation, airport, crew, other
- RASK estimated at ~1.10x CASK (industry margin)

### Phase 8: ML Predictions
- `services/ml_pipeline.py` — Feature importance, time series forecasts, cost regression, route profitability, fuel anomaly detection
- `api/routes/predictions.py` — REST endpoints for ML results
- Frontend predictions page with charts and tables

### Phase 9: Scenario Engine
- `services/scenario_engine.py` — What-if analysis with parameter modification
- `api/routes/scenarios.py` — CRUD + 8 preset scenarios
- Frontend scenarios page with preset buttons, custom builder, delta charts

### Database
6 new tables: `operational_kpis`, `economic_factors`, `unit_economics`, `ml_predictions`, `ml_feature_importance`, `scenarios`

---

## 2026-03-20 — Initial Commit (Phases 1-2)

- Real-time ADS-B ingestion from OpenSky Network
- Per-flight fuel burn and CO2 estimation via OpenAP
- Aircraft type enrichment, airline detection, route lookup
- TimescaleDB persistence, Redis live cache, WebSocket broadcast
- Next.js dashboard with live Leaflet map
- Docker Compose stack (TimescaleDB, Redis, FastAPI, Next.js)
