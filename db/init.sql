CREATE EXTENSION IF NOT EXISTS timescaledb;

-- ── State vectors (live time-series) ──────────────────────────────────────────
CREATE TABLE IF NOT EXISTS state_vectors (
    time             TIMESTAMPTZ      NOT NULL,
    icao24           TEXT             NOT NULL,
    callsign         TEXT,
    latitude         DOUBLE PRECISION,
    longitude        DOUBLE PRECISION,
    baro_altitude    DOUBLE PRECISION,
    velocity         DOUBLE PRECISION,
    heading          DOUBLE PRECISION,
    vertical_rate    DOUBLE PRECISION,
    on_ground        BOOLEAN,
    fuel_flow_kg_s   DOUBLE PRECISION,
    co2_kg_s         DOUBLE PRECISION
);

SELECT create_hypertable('state_vectors', 'time', if_not_exists => TRUE);

CREATE INDEX IF NOT EXISTS idx_sv_icao24_time
    ON state_vectors (icao24, time DESC);

-- ── Enriched historical flights ───────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS flights (
    flight_id        UUID             PRIMARY KEY DEFAULT gen_random_uuid(),
    icao24           TEXT             NOT NULL,
    callsign         TEXT,
    aircraft_type    TEXT,
    airline_code     TEXT,
    airline_name     TEXT,
    origin_icao      TEXT,
    destination_icao TEXT,
    first_seen       TIMESTAMPTZ,
    last_seen        TIMESTAMPTZ,
    distance_km      DOUBLE PRECISION,
    total_fuel_kg    DOUBLE PRECISION,
    total_co2_kg     DOUBLE PRECISION,
    max_altitude     DOUBLE PRECISION,
    avg_speed        DOUBLE PRECISION
);

CREATE INDEX IF NOT EXISTS idx_flights_icao24
    ON flights (icao24);
CREATE INDEX IF NOT EXISTS idx_flights_first_seen
    ON flights (first_seen DESC);

-- ── Aircraft registry (ICAO24 → type mapping) ─────────────────────────────────
CREATE TABLE IF NOT EXISTS aircraft_registry (
    icao24           TEXT             PRIMARY KEY,
    aircraft_type    TEXT,
    airline_code     TEXT,
    registration     TEXT,
    last_updated     TIMESTAMPTZ      DEFAULT NOW()
);

-- ── Route analytics ───────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS route_analytics (
    origin_icao      TEXT             NOT NULL,
    destination_icao TEXT             NOT NULL,
    flight_count     INTEGER          DEFAULT 0,
    avg_fuel_kg      DOUBLE PRECISION,
    avg_duration_min DOUBLE PRECISION,
    avg_co2_kg       DOUBLE PRECISION,
    avg_distance_km  DOUBLE PRECISION,
    last_updated     TIMESTAMPTZ      DEFAULT NOW(),
    PRIMARY KEY (origin_icao, destination_icao)
);

-- ── Route performance (baselines vs actuals) ────────────────────────────────
CREATE TABLE IF NOT EXISTS route_performance (
    id                   UUID             PRIMARY KEY DEFAULT gen_random_uuid(),
    origin_icao          TEXT             NOT NULL,
    destination_icao     TEXT             NOT NULL,
    -- Baselines (all-time rolling averages)
    baseline_duration_min DOUBLE PRECISION,
    baseline_fuel_kg      DOUBLE PRECISION,
    baseline_co2_kg       DOUBLE PRECISION,
    baseline_distance_km  DOUBLE PRECISION,
    -- Recent actuals (last 7 days)
    recent_avg_duration_min DOUBLE PRECISION,
    recent_avg_fuel_kg      DOUBLE PRECISION,
    recent_avg_co2_kg       DOUBLE PRECISION,
    recent_flight_count     INTEGER DEFAULT 0,
    -- Deviations (positive = worse than baseline)
    duration_deviation_pct  DOUBLE PRECISION,
    fuel_deviation_pct      DOUBLE PRECISION,
    co2_deviation_pct       DOUBLE PRECISION,
    -- Variability
    std_duration_min        DOUBLE PRECISION,
    std_fuel_kg             DOUBLE PRECISION,
    -- Scoring
    total_flight_count      INTEGER DEFAULT 0,
    performance_score       DOUBLE PRECISION,  -- -1 (underperforming) to +1 (overperforming)
    category                TEXT,              -- 'overperforming' | 'average' | 'underperforming'
    -- Fuel efficiency per km
    fuel_per_km             DOUBLE PRECISION,
    co2_per_km              DOUBLE PRECISION,
    -- Metadata
    updated_at              TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (origin_icao, destination_icao)
);

CREATE INDEX IF NOT EXISTS idx_route_performance_score
    ON route_performance (performance_score DESC);

-- ═══════════════════════════════════════════════════════════════════════════════
-- Phase 5: Operational KPIs
-- ═══════════════════════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS operational_kpis (
    id               UUID             PRIMARY KEY DEFAULT gen_random_uuid(),
    period_start     TIMESTAMPTZ      NOT NULL,
    period_end       TIMESTAMPTZ      NOT NULL,
    period_type      TEXT             NOT NULL,  -- 'weekly' or 'monthly'
    airline_code     TEXT             NOT NULL DEFAULT 'SWR',
    -- ASK / capacity
    total_ask        DOUBLE PRECISION,          -- Available Seat Kilometers
    -- Fleet utilization
    avg_block_hours_per_day DOUBLE PRECISION,
    total_block_hours       DOUBLE PRECISION,
    unique_aircraft_count   INTEGER,
    -- Route metrics
    total_departures INTEGER,
    unique_routes    INTEGER,
    -- Turnaround
    avg_turnaround_min  DOUBLE PRECISION,
    -- Fuel efficiency
    fuel_burn_per_ask   DOUBLE PRECISION,
    co2_per_ask         DOUBLE PRECISION,
    total_fuel_kg       DOUBLE PRECISION,
    total_co2_kg        DOUBLE PRECISION,
    -- Estimated load factor
    estimated_load_factor DOUBLE PRECISION,
    created_at       TIMESTAMPTZ      DEFAULT NOW(),
    UNIQUE (period_start, period_type, airline_code)
);

CREATE INDEX IF NOT EXISTS idx_kpis_period
    ON operational_kpis (period_start DESC, period_type);

-- ═══════════════════════════════════════════════════════════════════════════════
-- Phase 6: Economic Factors (external data time series)
-- ═══════════════════════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS economic_factors (
    date             DATE             NOT NULL,
    factor_name      TEXT             NOT NULL,
    value            DOUBLE PRECISION NOT NULL,
    unit             TEXT,
    source           TEXT,
    PRIMARY KEY (date, factor_name)
);

CREATE INDEX IF NOT EXISTS idx_economic_factor_name
    ON economic_factors (factor_name, date DESC);

-- ═══════════════════════════════════════════════════════════════════════════════
-- Phase 7: Unit Economics (CASK / RASK estimates)
-- ═══════════════════════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS unit_economics (
    id               UUID             PRIMARY KEY DEFAULT gen_random_uuid(),
    period_start     TIMESTAMPTZ      NOT NULL,
    period_end       TIMESTAMPTZ      NOT NULL,
    period_type      TEXT             NOT NULL,
    airline_code     TEXT             NOT NULL DEFAULT 'SWR',
    -- CASK components (CHF-cents per ASK)
    fuel_cost_per_ask    DOUBLE PRECISION,
    carbon_cost_per_ask  DOUBLE PRECISION,
    nav_charges_per_ask  DOUBLE PRECISION,
    airport_cost_per_ask DOUBLE PRECISION,
    crew_cost_per_ask    DOUBLE PRECISION,
    other_cost_per_ask   DOUBLE PRECISION,
    total_cask           DOUBLE PRECISION,
    -- RASK
    estimated_rask       DOUBLE PRECISION,
    -- Spread
    rask_cask_spread     DOUBLE PRECISION,
    -- Confidence
    confidence_level     TEXT DEFAULT 'estimate', -- 'estimate', 'validated', 'projected'
    created_at           TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (period_start, period_type, airline_code)
);

-- ═══════════════════════════════════════════════════════════════════════════════
-- Phase 8: ML Predictions & Feature Importance
-- ═══════════════════════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS ml_predictions (
    id                   UUID             PRIMARY KEY DEFAULT gen_random_uuid(),
    model_name           TEXT             NOT NULL,
    model_version        TEXT             NOT NULL,
    prediction_date      TIMESTAMPTZ      NOT NULL DEFAULT NOW(),
    target_period_start  TIMESTAMPTZ,
    target_period_end    TIMESTAMPTZ,
    target_variable      TEXT             NOT NULL,
    predicted_value      DOUBLE PRECISION NOT NULL,
    confidence_lower     DOUBLE PRECISION,
    confidence_upper     DOUBLE PRECISION,
    features_json        JSONB,
    created_at           TIMESTAMPTZ      DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_predictions_model
    ON ml_predictions (model_name, prediction_date DESC);

CREATE TABLE IF NOT EXISTS ml_feature_importance (
    id                UUID             PRIMARY KEY DEFAULT gen_random_uuid(),
    model_name        TEXT             NOT NULL,
    model_version     TEXT             NOT NULL,
    feature_name      TEXT             NOT NULL,
    importance_score  DOUBLE PRECISION NOT NULL,
    created_at        TIMESTAMPTZ      DEFAULT NOW()
);

-- ═══════════════════════════════════════════════════════════════════════════════
-- Phase 9: Scenario Engine
-- ═══════════════════════════════════════════════════════════════════════════════

-- ═══════════════════════════════════════════════════════════════════════════════
-- Flight Schedule Imputation
-- ═══════════════════════════════════════════════════════════════════════════════

-- Learned weekly schedule patterns (one row per callsign per day-of-week)
CREATE TABLE IF NOT EXISTS flight_schedule_patterns (
    id                   UUID             PRIMARY KEY DEFAULT gen_random_uuid(),
    callsign_norm        TEXT             NOT NULL,  -- e.g. "SWR8"
    day_of_week          SMALLINT         NOT NULL,  -- 0=Monday, 6=Sunday (ISO)
    typical_departure_utc TIME            NOT NULL,  -- median observed departure
    origin_icao          TEXT,
    destination_icao     TEXT,
    observation_count    INTEGER          NOT NULL DEFAULT 1,
    confidence           DOUBLE PRECISION NOT NULL DEFAULT 0.0, -- 0..1
    last_observed        TIMESTAMPTZ,
    created_at           TIMESTAMPTZ      DEFAULT NOW(),
    updated_at           TIMESTAMPTZ      DEFAULT NOW(),
    UNIQUE (callsign_norm, day_of_week)
);

CREATE INDEX IF NOT EXISTS idx_schedule_patterns_dow
    ON flight_schedule_patterns (day_of_week);

-- Imputed flights during offline gaps (never mixed with real observations)
CREATE TABLE IF NOT EXISTS imputed_flights (
    id                   UUID             PRIMARY KEY DEFAULT gen_random_uuid(),
    callsign_norm        TEXT             NOT NULL,
    expected_time        TIMESTAMPTZ      NOT NULL,  -- when we expected this flight
    origin_icao          TEXT,
    destination_icao     TEXT,
    status               TEXT             NOT NULL DEFAULT 'expected',
                                          -- 'expected' | 'confirmed' | 'missed'
    matched_flight_id    UUID REFERENCES flights(flight_id),
    pattern_confidence   DOUBLE PRECISION,
    created_at           TIMESTAMPTZ      DEFAULT NOW(),
    reconciled_at        TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_imputed_flights_time
    ON imputed_flights (expected_time DESC);
CREATE INDEX IF NOT EXISTS idx_imputed_flights_status
    ON imputed_flights (status);

CREATE TABLE IF NOT EXISTS scenarios (
    id               UUID             PRIMARY KEY DEFAULT gen_random_uuid(),
    name             TEXT             NOT NULL,
    description      TEXT,
    parameters       JSONB            NOT NULL,  -- e.g. {"fuel_price_change_pct": 20}
    results          JSONB,                      -- computed scenario output
    base_period_start TIMESTAMPTZ,
    base_period_end   TIMESTAMPTZ,
    status           TEXT             DEFAULT 'pending', -- 'pending','running','completed','failed'
    created_at       TIMESTAMPTZ      DEFAULT NOW()
);
