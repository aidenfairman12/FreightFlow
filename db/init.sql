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
    last_updated     TIMESTAMPTZ      DEFAULT NOW(),
    PRIMARY KEY (origin_icao, destination_icao)
);
