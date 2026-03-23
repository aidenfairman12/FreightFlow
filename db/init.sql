-- FreightFlow: US Freight Logistics Intelligence Platform
-- Database schema for FAF5 freight flow analysis

CREATE EXTENSION IF NOT EXISTS timescaledb;

-- ═══════════════════════════════════════════════════════════════════════════════
-- Reference Data
-- ═══════════════════════════════════════════════════════════════════════════════

-- FAF5 zone reference (132 domestic + international gateway zones)
CREATE TABLE IF NOT EXISTS faf_zones (
    zone_id          INTEGER          PRIMARY KEY,
    zone_name        TEXT             NOT NULL,
    state_fips       TEXT,
    state_name       TEXT,
    zone_type        TEXT,            -- 'metro', 'rest_of_state', 'port', etc.
    latitude         DOUBLE PRECISION,
    longitude        DOUBLE PRECISION
);

-- SCTG commodity codes
CREATE TABLE IF NOT EXISTS commodities (
    sctg2            TEXT             PRIMARY KEY,
    commodity_name   TEXT             NOT NULL,
    commodity_group  TEXT
);

-- ═══════════════════════════════════════════════════════════════════════════════
-- Core Freight Data
-- ═══════════════════════════════════════════════════════════════════════════════

-- FAF5 freight flows (one row per origin-destination-commodity-mode-year)
CREATE TABLE IF NOT EXISTS freight_flows (
    id               UUID             PRIMARY KEY DEFAULT gen_random_uuid(),
    origin_zone_id   INTEGER          NOT NULL REFERENCES faf_zones(zone_id),
    dest_zone_id     INTEGER          NOT NULL REFERENCES faf_zones(zone_id),
    sctg2            TEXT             NOT NULL REFERENCES commodities(sctg2),
    mode_code        INTEGER          NOT NULL,
    mode_name        TEXT             NOT NULL,
    year             INTEGER          NOT NULL,
    data_type        TEXT             NOT NULL DEFAULT 'historical',
    tons_thousands   DOUBLE PRECISION,
    value_millions   DOUBLE PRECISION,
    ton_miles_millions DOUBLE PRECISION,
    UNIQUE (origin_zone_id, dest_zone_id, sctg2, mode_code, year)
);

CREATE INDEX IF NOT EXISTS idx_ff_origin_dest ON freight_flows (origin_zone_id, dest_zone_id);
CREATE INDEX IF NOT EXISTS idx_ff_commodity ON freight_flows (sctg2);
CREATE INDEX IF NOT EXISTS idx_ff_mode ON freight_flows (mode_code);
CREATE INDEX IF NOT EXISTS idx_ff_year ON freight_flows (year);

-- Curated corridor definitions (2-3 major freight corridors)
CREATE TABLE IF NOT EXISTS corridors (
    corridor_id      UUID             PRIMARY KEY DEFAULT gen_random_uuid(),
    name             TEXT             NOT NULL UNIQUE,
    description      TEXT,
    origin_zones     INTEGER[]        NOT NULL,
    dest_zones       INTEGER[]        NOT NULL,
    origin_lat       DOUBLE PRECISION,
    origin_lon       DOUBLE PRECISION,
    dest_lat         DOUBLE PRECISION,
    dest_lon         DOUBLE PRECISION,
    created_at       TIMESTAMPTZ      DEFAULT NOW()
);

-- ═══════════════════════════════════════════════════════════════════════════════
-- Cost Model
-- ═══════════════════════════════════════════════════════════════════════════════

-- Freight rates per ton-mile by mode and year
CREATE TABLE IF NOT EXISTS freight_rates (
    id               UUID             PRIMARY KEY DEFAULT gen_random_uuid(),
    mode_code        INTEGER          NOT NULL,
    mode_name        TEXT             NOT NULL,
    year             INTEGER          NOT NULL,
    cost_per_ton_mile_usd DOUBLE PRECISION NOT NULL,
    source           TEXT,
    notes            TEXT,
    UNIQUE (mode_code, year)
);

-- ═══════════════════════════════════════════════════════════════════════════════
-- Analytics & KPIs
-- ═══════════════════════════════════════════════════════════════════════════════

-- Corridor performance (aggregated metrics per corridor per year)
CREATE TABLE IF NOT EXISTS corridor_performance (
    id               UUID             PRIMARY KEY DEFAULT gen_random_uuid(),
    corridor_id      UUID             REFERENCES corridors(corridor_id),
    year             INTEGER          NOT NULL,
    sctg2            TEXT,
    total_tons       DOUBLE PRECISION,
    total_value_usd  DOUBLE PRECISION,
    total_ton_miles  DOUBLE PRECISION,
    mode_breakdown   JSONB,
    avg_value_per_ton DOUBLE PRECISION,
    estimated_cost   DOUBLE PRECISION,
    cost_per_ton     DOUBLE PRECISION,
    updated_at       TIMESTAMPTZ      DEFAULT NOW(),
    UNIQUE (corridor_id, year, sctg2)
);

-- Freight KPIs (periodic aggregations)
CREATE TABLE IF NOT EXISTS freight_kpis (
    id               UUID             PRIMARY KEY DEFAULT gen_random_uuid(),
    period_year      INTEGER          NOT NULL,
    scope            TEXT             NOT NULL DEFAULT 'national',
    total_tons       DOUBLE PRECISION,
    total_value_usd  DOUBLE PRECISION,
    total_ton_miles  DOUBLE PRECISION,
    truck_share_pct  DOUBLE PRECISION,
    rail_share_pct   DOUBLE PRECISION,
    air_share_pct    DOUBLE PRECISION,
    water_share_pct  DOUBLE PRECISION,
    multi_share_pct  DOUBLE PRECISION,
    avg_cost_per_ton_mile DOUBLE PRECISION,
    total_estimated_cost  DOUBLE PRECISION,
    value_per_ton    DOUBLE PRECISION,
    ton_miles_per_ton DOUBLE PRECISION,
    created_at       TIMESTAMPTZ      DEFAULT NOW(),
    UNIQUE (period_year, scope)
);

-- Freight unit economics (cost breakdown per ton-mile)
CREATE TABLE IF NOT EXISTS freight_unit_economics (
    id               UUID             PRIMARY KEY DEFAULT gen_random_uuid(),
    year             INTEGER          NOT NULL,
    scope            TEXT             NOT NULL DEFAULT 'national',
    fuel_cost_per_tm     DOUBLE PRECISION,
    labor_cost_per_tm    DOUBLE PRECISION,
    equipment_cost_per_tm DOUBLE PRECISION,
    insurance_cost_per_tm DOUBLE PRECISION,
    tolls_fees_per_tm    DOUBLE PRECISION,
    other_cost_per_tm    DOUBLE PRECISION,
    total_cost_per_tm    DOUBLE PRECISION,
    revenue_per_tm       DOUBLE PRECISION,
    margin_per_tm        DOUBLE PRECISION,
    confidence_level     TEXT DEFAULT 'estimate',
    created_at           TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (year, scope)
);

-- ═══════════════════════════════════════════════════════════════════════════════
-- Economic Factors (external data time series)
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
-- Scenario Engine
-- ═══════════════════════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS scenarios (
    id               UUID             PRIMARY KEY DEFAULT gen_random_uuid(),
    name             TEXT             NOT NULL,
    description      TEXT,
    parameters       JSONB            NOT NULL,
    results          JSONB,
    base_period_start TIMESTAMPTZ,
    base_period_end   TIMESTAMPTZ,
    status           TEXT             DEFAULT 'pending',
    created_at       TIMESTAMPTZ      DEFAULT NOW()
);
