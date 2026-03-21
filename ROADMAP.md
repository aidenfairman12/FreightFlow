# PlaneLogistics — Project Roadmap

Swiss Airspace Real-Time Logistics Analytics Platform → SWISS Airline Intelligence Platform

---

## Phase 1 — Live Map (COMPLETE)
**Goal**: Wire the data pipeline and display live flight positions on a map.

- [x] OpenSky OAuth2 polling (global, filtered to SWR, every 30s with credit management)
- [x] Redis live cache for current flight state
- [x] WebSocket broadcast to connected browsers
- [x] Leaflet map with real-time aircraft markers (heading-rotated icons)
- [x] Flight sidebar with basic info (callsign, altitude, speed, heading)
- [x] CORS, Docker Compose, TimescaleDB schema

---

## Phase 2 — Fuel Modeling + Persistence + Analytics (COMPLETE)
**Goal**: Enrich broadcasts with fuel/CO2 estimates, persist data, and serve analytics.

- [x] Fuel/CO2 estimation via OpenAP (`fuel_flow_kg_s`, `co2_kg_s`)
  - scipy monkey-patch for compatibility with openap 1.3
- [x] TimescaleDB persistence — batch INSERT every poll cycle (`state_vectors`)
- [x] Background aircraft type lookup (OpenSky metadata API, in-memory cache)
- [x] Background route lookup (origin/destination, 2h TTL, 5min retry on failure)
- [x] `/analytics/emissions` — fleet-wide CO2/fuel totals (last 10 min)
- [x] `/analytics/fuel` — top 20 fuel consumers (last 1 hour)
- [x] Fleet summary strip on dashboard (aircraft count, fuel rate, CO2 rate)
- [x] Fuel rate + CO2 rate rows in flight info sidebar

---

## Phase 3 — Historical Replay + Flight Aggregation (PARTIAL — see Phase 14)
**Goal**: Aggregate flights and support historical queries.

- [x] Flight aggregation: state_vectors → flights table (completed flight detection)
- [x] Periodic aggregation job (every 5 minutes via APScheduler)
- [ ] ~~Remaining items moved to Phase 14~~

---

## Phase 4 — ML Foundations (COMPLETE — absorbed into Phases 5, 8, 10)
**Goal**: Route analytics and anomaly detection.

- [x] Route frequency analytics (moved to Phase 5 KPI pipeline + Phase 10 frontend)
- [x] Fuel anomaly detection (implemented in Phase 8 ML pipeline)
- [x] Route performance baselines + deviation scoring (Phase 10)

---

## Phase 5 — Operational KPI Pipeline (COMPLETE)
**Goal**: SWISS-specific airline-analyst-grade operational metrics.

- [x] SWISS flight filtering (SWR callsign prefix)
- [x] Aircraft seat count database (30+ types, SWISS fleet + common types)
- [x] ASK (Available Seat Kilometers) computation
- [x] Fleet utilization: block hours per aircraft per day
- [x] Route frequency: departures per route per period
- [x] Turnaround time estimation (ground time between flights)
- [x] Fuel burn per ASK aggregation
- [x] Weekly/monthly KPI aggregation with upsert
- [x] `/kpi/current`, `/kpi/history`, `/kpi/fleet`, `/kpi/routes` endpoints
- [x] KPI dashboard page with cards, trend charts, fleet table
- [x] Hourly scheduled KPI computation

---

## Phase 6 — External Financial Data Pipeline (COMPLETE)
**Goal**: Ingest publicly available cost and revenue drivers.

- [x] ECB exchange rates (EUR/CHF, USD/CHF) — free XML feed
- [x] EIA jet fuel & Brent crude prices (requires EIA_API_KEY)
- [x] EU ETS carbon price (Ember Climate API + fallback estimate)
- [x] `economic_factors` table with date-indexed time series
- [x] `/economics/latest`, `/economics/history/{factor}` endpoints
- [x] 6-hourly scheduled ETL
- [x] Economic indicators dashboard with live factor cards

---

## Phase 7 — Unit Economics Modeling (COMPLETE)
**Goal**: Estimate SWISS CASK and RASK from public data.

- [x] CASK component estimation:
  - Fuel cost per ASK (fuel burn × jet fuel price)
  - Carbon cost per ASK (CO2 × EUA price)
  - Navigation charges per ASK (Eurocontrol unit rates)
  - Airport cost per ASK (ZRH landing + passenger fees)
  - Crew cost per ASK (block hours × benchmark rates)
  - Other costs (derived from industry cost breakdown proportions)
- [x] RASK estimation (margin-based from CASK)
- [x] RASK-CASK spread tracking
- [x] `unit_economics` table with period-based storage
- [x] `/economics/unit-economics/*`, `/economics/cask-breakdown` endpoints
- [x] CASK breakdown pie chart, CASK vs RASK trend, stacked component chart

---

## Phase 8 — Predictive Models (COMPLETE)
**Goal**: ML pipeline for forecasting and anomaly detection.

- [x] Feature importance — RandomForest identifying CASK/yield drivers
- [x] Time series forecasting — Linear extrapolation with confidence bands
- [x] Cost regression — GradientBoosting predicting total CASK
- [x] Route profitability scoring — frequency + fuel efficiency composite score
- [x] Fuel anomaly detection — z-score based flagging of unusual burn rates
- [x] `ml_predictions` + `ml_feature_importance` tables
- [x] `/predictions/*` endpoints (feature importance, forecasts, anomalies, routes)
- [x] ML dashboard with feature importance bars, forecast charts, anomaly table
- [x] On-demand model training trigger
- [x] scikit-learn + LightGBM dependencies

---

## Phase 9 — Scenario Engine (COMPLETE)
**Goal**: What-if analysis for strategic decisions.

- [x] Scenario parameter system:
  - Fuel price change (%)
  - Carbon price change (%)
  - Load factor change (%)
  - Capacity change (%)
  - EUR/CHF exchange rate change (%)
  - New weekly departures
- [x] Baseline CASK/RASK loading + scenario recomputation
- [x] Delta calculation for all components
- [x] Human-readable impact summaries
- [x] 8 preset scenarios (fuel spike, carbon surge, capacity expansion, stagflation, etc.)
- [x] Custom scenario builder (frontend form)
- [x] Scenario persistence + history
- [x] `/scenarios/*` endpoints (CRUD + presets)
- [x] Interactive scenario page with presets, builder, results, and history

---

## Phase 10 — Frontend Platform Upgrade (COMPLETE)
**Goal**: Shared component library, full backend coverage in the UI, and code quality improvements.

- [x] Shared component library: Card, DataTable, LoadingSpinner, ErrorBanner, EmptyState, StatusBadge
- [x] Centralized theme system (`styles/theme.ts` — colors, card/label/tooltip/button styles)
- [x] `useApiData<T>` hook replacing all raw `fetch()` + `useEffect` patterns
- [x] New Schedule page (pattern heatmap, imputed flights table, summary cards)
- [x] Route performance section on Analytics page (category filters, deviation table)
- [x] Route frequency bar chart on Analytics page
- [x] Factor history drilldown on Economics page (click indicator → 90-day chart)
- [x] Trained Models card on Predictions page
- [x] All pages refactored to typed API client + shared components
- [x] 80-test backend test suite (pytest)
- [x] OpenSky daily credit limit protection (4000/day budget, 30s poll interval)

---

## Phase 11 — Frontend Performance & Polish (NEXT)
**Goal**: Optimize frontend speed and responsiveness.

- [ ] Diagnose dev mode vs production build performance
- [ ] Profile and fix unnecessary re-renders (React DevTools)
- [ ] Lazy-load heavy Recharts components on data pages
- [ ] Optimize `useApiData` polling (pause when tab hidden, stale-while-revalidate)
- [ ] Production build optimizations (bundle analysis, code splitting)

---

## Phase 12 — Metric Refinement & Data Validation
**Goal**: Validate all computed metrics against real-world data and published figures.

- [ ] Collect 48+ hours of continuous ADS-B data
- [ ] Validate KPI computations against expected ranges
- [ ] Validate CASK/RASK estimates against Lufthansa Group published figures
- [ ] Tune estimation constants based on observed data patterns
- [ ] Improve schedule pattern learning with more observations

---

## Phase 13 — Lufthansa Group Fuel Cost Modeling (FUTURE)
**Goal**: Accurately model the relationship between market fuel prices and what Lufthansa Group actually pays.

- [ ] Research Lufthansa Group annual/quarterly reports for fuel hedging ratios and avg fuel costs
- [ ] Model hedging strategy (typically 60-80% hedged 12-24 months forward)
- [ ] Build lagged/smoothed fuel price model (spot price → actual cost paid)
- [ ] Integrate improved fuel cost into CASK computation
- [ ] Validate against published Lufthansa Group fuel cost per ASK figures

---

## Phase 14 — Historical Replay & Weather (from original Phases 3-4)
**Goal**: Time-travel through collected data and add weather context.

- [ ] Time range picker for analytics queries
- [ ] Historical replay scrubber for map
- [ ] METAR weather overlay for Swiss airports
- [ ] Route frequency network visualization

---

## Architecture Summary

```
Frontend Pages:
  /dashboard     — Live map + flight sidebar (Phase 1-2)
  /analytics     — SWISS operational KPIs + route performance (Phase 5, 10)
  /economics     — Financial intelligence + CASK/RASK (Phase 6-7)
  /predictions   — ML models + anomaly detection (Phase 8)
  /scenarios     — What-if scenario engine (Phase 9)
  /schedule      — Flight schedule patterns + imputation (Phase 10)

Backend Routes:
  /flights/*      — Live + historical flights
  /analytics/*    — Fuel, emissions, route performance
  /kpi/*          — Operational KPIs
  /economics/*    — Economic factors + unit economics
  /predictions/*  — ML predictions + anomalies
  /scenarios/*    — Scenario engine
  /schedule/*     — Schedule patterns + imputed flights

Scheduled Jobs:
  Every 30s       — OpenSky polling + enrichment + broadcast (credit-managed)
  Every 5min      — Flight aggregation (state_vectors → flights)
  Every 1hr       — SWISS KPI computation + unit economics
  Every 1hr       — Schedule imputation (learn + reconcile)
  Every 1hr       — Route performance (baselines + deviations)
  Every 6hrs      — Economic data ETL (ECB, EIA, carbon)

Database Tables:
  state_vectors          — TimescaleDB hypertable, one row per poll per aircraft
  flights                — Enriched completed flights
  aircraft_registry      — ICAO24 → aircraft type cache
  route_analytics        — Aggregated route stats
  route_performance      — Per-route baselines vs actuals, deviation scores
  operational_kpis       — Weekly/monthly SWISS KPIs
  economic_factors       — Time-series economic data
  unit_economics         — CASK/RASK estimates
  ml_predictions         — Model predictions
  ml_feature_importance  — Feature importance scores
  scenarios              — What-if scenarios + results
  flight_schedule_patterns — Learned weekly schedule
  imputed_flights        — Expected flights during offline gaps
```
