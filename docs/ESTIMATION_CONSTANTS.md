# Estimation Constants & Assumptions

Every calculated metric in PlaneLogistics relies on assumptions and estimated values. This document catalogs all of them so they can be audited, calibrated, and improved as real data accumulates.

**Rule:** When adding a new estimation constant anywhere in the codebase, add it to this document with its value, rationale, and the file where it lives.

---

## Aircraft Performance

| Constant | Value | File | Rationale |
|----------|-------|------|-----------|
| Cruise mass estimate | 75% of MTOW per type | `aircraft_data.py` | Mid-flight aircraft are lighter than MTOW (fuel burned off, not max payload) but heavier than OEW. 75% is a standard industry approximation for mid-cruise weight. |
| Default cruise mass (unknown type) | 65,000 kg | `aircraft_data.py` | Approximate mid-cruise mass of a generic narrowbody (A320 family). Used only when aircraft type is unresolved. |
| Cruise speed per type | Per-type (510-903 km/h) | `aircraft_data.py` | Manufacturer-published typical cruise speeds. ATR 72 = 510, A320 family = ~828, 777 = 892 km/h. |
| Default cruise speed (unknown type) | 800 km/h | `aircraft_data.py` | Weighted average of SWISS fleet cruise speeds, biased toward narrowbody majority. |
| Seat counts per type | Per-type (72-340) | `aircraft_data.py` | Typical 2-class configuration for each aircraft type. SWISS-specific where possible (e.g., A330-300 = 236, A350-900 = 293 seats in SWISS config). Fleet data from Lufthansa Group 2025 annual report. |
| Default seat count (unknown type) | 170 | `aircraft_data.py` | Approximate capacity of the most common SWISS aircraft (A320/A220 family). |
| Velocity threshold for fuel calc | 50 m/s (~97 kts) | `fuel_model.py` | Below this speed, aircraft is likely taxiing or on approach — OpenAP enroute model is not valid. |
| Default aircraft type fallback | A320 | `fuel_model.py` | When ICAO24 → type lookup fails, assume A320 characteristics. The A320 family is the most common SWISS type, so this minimizes average error. |

## Fuel & Emissions

| Constant | Value | File | Rationale |
|----------|-------|------|-----------|
| Fuel flow integration | Actual time delta (capped 60s) | `flight_aggregator.py`, `kpi_aggregator.py` | Uses LAG window function to compute real seconds between consecutive state vectors. Capped at 60s to prevent data gaps from inflating totals. First sample for each aircraft defaults to 10s. |
| CO2 per kg fuel | Computed by OpenAP | `fuel_model.py` | OpenAP's Emission model computes CO2 from fuel flow rate using ICAO emissions databank factors per engine type. Not a hardcoded constant. |
| Jet fuel density | 3.1 kg/gal | `unit_economics.py` | Standard jet fuel (Jet A-1) density. Used to convert fuel mass to volume for price calculations (EIA reports $/gallon). Actual density varies 2.97-3.24 kg/gal with temperature. |

## Load Factors

| Constant | Value | File | Rationale |
|----------|-------|------|-----------|
| Regional aircraft LF | 0.72 (72%) | `aircraft_data.py` | Regional routes serve thinner markets with less pricing optimization. Based on Lufthansa Group 2023 annual report (Eurowings/regional segment). |
| Narrowbody LF | 0.82 (82%) | `aircraft_data.py` | European short/medium-haul average. Lufthansa Group Network Airlines reported ~82% system LF for intra-European routes in 2023. |
| Widebody LF | 0.87 (87%) | `aircraft_data.py` | Intercontinental long-haul routes run higher load factors due to fewer frequencies and stronger yield management. LH Group Network Airlines reported ~86-88% for long-haul in 2023. |
| Default LF (unknown type) | 0.82 | `aircraft_data.py` | Falls back to narrowbody average since the SWISS fleet is majority narrowbody. |
| Fleet-weighted LF | Computed per period | `kpi_aggregator.py` | Weighted average across all aircraft types observed in the period, using the category-based factors above. |

## KPI Computation

| Constant | Value | File | Rationale |
|----------|-------|------|-----------|
| Block hours integration | Actual time delta (capped 60s) | `kpi_aggregator.py` | Same LAG-based approach as fuel. Sums real seconds where `on_ground = false`, converted to hours. |
| Flight segment bucket | 5 minutes | `kpi_aggregator.py` | TimescaleDB `time_bucket` groups state vectors into 5-minute windows to identify distinct flight segments. Gaps >5 min between observations = separate segment. |
| Min observations per segment | 6 | `kpi_aggregator.py` | At least 6 state vectors (~1 minute of tracking at 10s intervals) required to count as a valid flight segment. Filters noise. |
| Turnaround time bounds | 600-14,400s (10 min - 4 hrs) | `kpi_aggregator.py` | Realistic turnaround range. <10 min is likely a data artifact (touch-and-go, sensor gap). >4 hrs is likely an aircraft swap or overnight. SWISS short-haul turnaround is typically 30-60 min. |

## Unit Economics (CASK/RASK)

| Constant | Value | File | Rationale |
|----------|-------|------|-----------|
| CASK component split: fuel | 28% | `unit_economics.py` | IATA 2023 industry cost breakdown. Fuel is the largest single cost component for airlines. Used to back-calculate total CASK from the fuel component we can estimate directly. |
| CASK component split: carbon | 3% | `unit_economics.py` | EU ETS costs are growing but still a small share. Based on 2023 data; expected to rise as free allowances phase out by 2026. |
| CASK component split: navigation | 7% | `unit_economics.py` | Eurocontrol/ANSP charges. Relatively stable across European carriers. |
| CASK component split: airport | 10% | `unit_economics.py` | Landing fees, terminal charges, ground handling. ZRH is an expensive hub which pushes this higher for SWISS. |
| CASK component split: crew | 25% | `unit_economics.py` | Flight deck + cabin crew wages, training, hotels. Swiss labor costs are high; 25% is conservative (could be higher). |
| CASK component split: other | 27% | `unit_economics.py` | Maintenance, aircraft lease, depreciation, admin, sales/distribution. Residual category. |
| Eurocontrol nav rate | 108 CHF | `unit_economics.py` | Swiss unit rate per service unit (per 100 km at reference weight). From Eurocontrol published charging tables. Updated annually. |
| ZRH landing fee | 1,200 CHF | `unit_economics.py` | Average per-movement charge at Zurich Airport. From Flughafen Zurich AG published schedule of charges. Varies by aircraft weight and time of day. |
| ZRH passenger fee | 35 CHF | `unit_economics.py` | Per departing passenger charge. Includes security, infrastructure, noise surcharge. From ZRH published tariffs. |
| Crew cost per block hour | 1,800 CHF | `unit_economics.py` | Combined flight deck + cabin crew cost estimate. Swiss wage levels are ~20-30% above EU average. Based on Lufthansa Group segment reporting and Swiss labor market data. |
| RASK/CASK margin | 1.10 (10%) | `unit_economics.py` | Assumes SWISS earns ~10% operating margin. Lufthansa Group Network Airlines segment typically reports 8-12% EBIT margin in profitable years. This is a rough proxy; actual SWISS margin is not published separately. |

## Economic Factor Fallbacks

These are used only when the ETL pipeline has not yet fetched real data.

| Constant | Value | File | Rationale |
|----------|-------|------|-----------|
| Jet fuel price fallback | $2.80/gal | `unit_economics.py`, `scenario_engine.py` | Approximate mid-2024 US Gulf Coast kerosene price. Replaced by real EIA data once ETL runs. |
| EUA carbon price fallback | 65 EUR/ton | `unit_economics.py`, `scenario_engine.py` | Approximate mid-2024 EU ETS price. Replaced by real data once ETL runs. |
| EUR/CHF fallback | 0.95 | `unit_economics.py`, `scenario_engine.py` | Approximate 2024 exchange rate. Replaced by real ECB data once ETL runs. |
| USD/CHF fallback | 0.88 | `unit_economics.py`, `scenario_engine.py` | Approximate 2024 exchange rate. Replaced by real ECB data once ETL runs. |
| Carbon price fallback (ETL) | 65 EUR/ton | `economic_etl.py` | Same as above; used if Ember API is unavailable. |

## Flight Aggregation

| Constant | Value | File | Rationale |
|----------|-------|------|-----------|
| "Recently active" window | 30 min | `flight_aggregator.py` | Aircraft must have state vectors in the last 30 minutes to be candidates for aggregation. Covers longest typical poll gap. |
| Completion threshold | 3 min | `flight_aggregator.py` | Aircraft not seen for 3+ minutes is considered to have completed its tracked segment. Allows for brief signal drops without premature aggregation. |
| Min observations for flight | 12 | `flight_aggregator.py` | At 10s poll interval, 12 observations = ~2 minutes of tracking. Filters out brief radar contacts that aren't meaningful flights. |
| Min flight duration | 120s | `flight_aggregator.py` | Flight must span >2 minutes of wall-clock time. Prevents noise from being recorded as flights. |
| De-duplication window | 35 min | `flight_aggregator.py` | Check existing flights within 35 minutes to avoid re-inserting the same flight. Slightly wider than the 30-min active window for safety. |
| Time delta cap | 60s | `flight_aggregator.py` | When computing fuel/CO2 totals from time deltas, cap each sample at 60 seconds. Prevents a 5-minute data gap from being counted as 5 minutes of fuel burn at the last observed rate. |

## Schedule Imputation

| Constant | Value | File | Rationale |
|----------|-------|------|-----------|
| Min confidence observations | 3 | `schedule_imputation.py` | A pattern needs at least 3 observations before it's used for imputation. Prevents one-off flights from being treated as scheduled. |
| Match window | 3 hours | `schedule_imputation.py` | A real flight within +-3 hours of an expected time "confirms" the imputed flight. Accounts for delays, schedule changes, and time zone ambiguity. |
| Learning lookback | 30 days | `schedule_imputation.py` | Patterns are learned from the last 30 days of flight data. Balances having enough observations with reflecting current schedule (SWISS adjusts seasonally). |
| Confidence threshold | 10 observations | `schedule_imputation.py` | `confidence = min(observations / 10, 1.0)`. 10 observations over 30 days = max confidence. A daily flight would hit this in ~2 weeks. |
| Offline gap threshold | 20 min | `schedule_imputation.py` | A gap >20 minutes between state_vectors triggers imputation. Normal polling is 10-30 seconds, so 20 min clearly indicates downtime. |

## Route Performance

| Constant | Value | File | Rationale |
|----------|-------|------|-----------|
| Recent window | 7 days | `route_performance.py` | Compare last 7 days of flights against all-time baseline. Short enough to catch recent changes, long enough for statistical significance on frequent routes. |
| Min flights for baseline | 3 | `route_performance.py` | Routes need at least 3 historical flights before we compute a baseline. Prevents noisy scoring on rarely-flown routes. |
| Min recent flights | 2 | `route_performance.py` | Need at least 2 recent flights to compute a meaningful recent average. |
| Performance score weights | Fuel 50%, Duration 30%, CO2 20% | `route_performance.py` | Fuel is the primary cost driver and most actionable. Duration affects crew costs and aircraft utilization. CO2 is partially redundant with fuel but captures emissions-specific factors. |
| Over/underperformance threshold | +-5% | `route_performance.py` | Routes within +-5% of baseline are "average". Beyond that, they're flagged. 5% is roughly one standard deviation for well-established routes. |

## ML Pipeline

| Constant | Value | File | Rationale |
|----------|-------|------|-----------|
| Min training data | 4 rows | `ml_pipeline.py` | Need at least 4 historical periods to train any model. Fewer than this and cross-validation is meaningless. |
| RandomForest config | 100 trees, max_depth=5 | `ml_pipeline.py` | Standard scikit-learn defaults with limited depth to prevent overfitting on small airline datasets. |
| GradientBoosting config | 100 estimators, depth=3, lr=0.1 | `ml_pipeline.py` | Conservative boosting parameters. Small learning rate + limited depth for stable estimates on limited data. |
| Cross-validation folds | 3 | `ml_pipeline.py` | `min(3, len(data))`. Small fold count because we typically have weeks-to-months of data, not thousands of samples. |
| Forecast horizon | 4 periods | `ml_pipeline.py` | Forecast 4 weeks ahead. Beyond this, airline economics become increasingly unpredictable (fuel prices, demand shifts). |
| Anomaly Z-score threshold | 2.0 | `ml_pipeline.py` | Flag flights where fuel burn deviates >2 standard deviations from the aircraft's mean. Catches ~5% of flights as potential anomalies. |
| Route profitability weights | Frequency 60%, Efficiency 40% | `ml_pipeline.py` | High-frequency routes are more likely profitable (airlines don't fly unprofitable routes often). Fuel efficiency is the secondary signal. |
| Profitability thresholds | >0.6 profitable, 0.3-0.6 marginal | `ml_pipeline.py` | Arbitrary score boundaries for categorization. Should be calibrated against actual route profitability data if available. |
| 95% confidence interval | Z = 1.96 | `ml_pipeline.py` | Standard normal Z-score for 95% confidence bands on forecasts. |

---

## How to Update This Document

When adding a new estimated or hardcoded value:

1. Add a row to the appropriate section above
2. Include: what the constant is, its value, which file it lives in, and **why** that value was chosen
3. If the value came from a specific source (e.g., "IATA 2023 cost breakdown"), cite it
4. If the value is a known simplification, note what would improve it

When calibrating a value against real data:
1. Update the value in code
2. Update this document
3. Note the calibration source and date in the rationale
