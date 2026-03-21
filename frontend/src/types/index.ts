export interface StateVector {
  icao24: string
  callsign: string | null
  origin_country: string | null
  latitude: number | null
  longitude: number | null
  baro_altitude: number | null
  on_ground: boolean
  velocity: number | null
  heading: number | null
  vertical_rate: number | null
  geo_altitude: number | null
  squawk: string | null
  last_contact: string
  // Populated after Phase 1 enrichment
  aircraft_type?: string | null
  airline_name?: string | null
  origin_airport?: string | null
  destination_airport?: string | null
  fuel_flow_kg_s?: number | null
  co2_kg_s?: number | null
}

export interface EnrichedFlight {
  flight_id: string
  icao24: string
  callsign: string | null
  aircraft_type: string | null
  airline_name: string | null
  origin_icao: string | null
  destination_icao: string | null
  first_seen: string | null
  last_seen: string | null
  distance_km: number | null
  total_fuel_kg: number | null
  total_co2_kg: number | null
  max_altitude: number | null
  avg_speed: number | null
}

export interface ApiResponse<T> {
  data: T
  error: string | null
  meta: Record<string, unknown>
}

// ── Phase 5: Operational KPIs ──────────────────────────────────────────────

export interface OperationalKPI {
  id: string
  period_start: string
  period_end: string
  period_type: string
  airline_code: string
  total_ask: number | null
  avg_block_hours_per_day: number | null
  total_block_hours: number | null
  unique_aircraft_count: number | null
  total_departures: number | null
  unique_routes: number | null
  avg_turnaround_min: number | null
  fuel_burn_per_ask: number | null
  co2_per_ask: number | null
  total_fuel_kg: number | null
  total_co2_kg: number | null
  estimated_load_factor: number | null
}

export interface FleetAircraft {
  icao24: string
  callsign: string | null
  block_hours: number
  observations: number
  first_seen: string
  last_seen: string
  avg_fuel: number | null
}

// ── Phase 6: Economics ─────────────────────────────────────────────────────

export interface EconomicFactors {
  [key: string]: {
    value: number
    unit: string
    source: string
    date: string
  }
}

export interface CASKBreakdown {
  components: {
    fuel: number
    carbon: number
    navigation: number
    airport: number
    crew: number
    other: number
  }
  total_cask: number
  period: string | null
}

export interface UnitEconomics {
  id: string
  period_start: string
  period_end: string
  fuel_cost_per_ask: number | null
  carbon_cost_per_ask: number | null
  nav_charges_per_ask: number | null
  airport_cost_per_ask: number | null
  crew_cost_per_ask: number | null
  other_cost_per_ask: number | null
  total_cask: number | null
  estimated_rask: number | null
  rask_cask_spread: number | null
  confidence_level: string
}

// ── Phase 8: ML Predictions ────────────────────────────────────────────────

export interface FeatureImportance {
  feature_name: string
  importance_score: number
}

export interface Prediction {
  model_name: string
  model_version: string
  target_variable: string
  predicted_value: number
  confidence_lower: number | null
  confidence_upper: number | null
  target_period_start: string | null
  target_period_end: string | null
  prediction_date: string
}

export interface FuelAnomaly {
  icao24: string
  callsign: string | null
  avg_fuel: number
  z_score: number
  samples: number
}

export interface RouteProfitability {
  origin_icao: string
  destination_icao: string
  flight_count: number
  avg_fuel_kg: number | null
  avg_duration_min: number | null
  profitability_score: number
  category: string
}

// ── Route Performance ──────────────────────────────────────────────────────

export interface RoutePerformance {
  origin_icao: string
  destination_icao: string
  total_flights: number
  baseline_duration_min: number | null
  recent_duration_min: number | null
  duration_deviation_pct: number | null
  baseline_fuel_kg: number | null
  recent_fuel_kg: number | null
  fuel_deviation_pct: number | null
  performance_score: number | null
  category: 'overperforming' | 'average' | 'underperforming'
  last_updated: string
}

export interface FlightDeviation {
  flight_id: string
  callsign: string | null
  origin_icao: string | null
  destination_icao: string | null
  duration_min: number | null
  baseline_duration_min: number | null
  duration_deviation_pct: number | null
  fuel_kg: number | null
  baseline_fuel_kg: number | null
  fuel_deviation_pct: number | null
  first_seen: string | null
}

// ── Schedule ───────────────────────────────────────────────────────────────

export interface SchedulePattern {
  callsign: string
  day_of_week: number
  typical_departure_utc: string
  origin_icao: string | null
  destination_icao: string | null
  observation_count: number
  confidence: number
  last_observed: string
}

export interface ImputedFlight {
  id: string
  callsign: string
  expected_departure: string
  origin_icao: string | null
  destination_icao: string | null
  status: 'expected' | 'confirmed' | 'missed'
  confidence: number
  matched_flight_id: string | null
  created_at: string
}

// ── ML Models ──────────────────────────────────────────────────────────────

export interface MLModel {
  model_name: string
  model_version: string
  feature_count?: number
  target_variable?: string
  prediction_count?: number
  last_trained?: string
  last_predicted?: string
}

// ── Phase 9: Scenarios ─────────────────────────────────────────────────────

export interface ScenarioPreset {
  name: string
  description: string
  parameters: Record<string, number>
}

export interface Scenario {
  id: string
  name: string
  description: string | null
  parameters: Record<string, number>
  results: ScenarioResults | null
  status: string
  created_at: string
}

export interface ScenarioResults {
  baseline: {
    total_cask: number
    estimated_rask: number
    spread: number
    fuel_cost_per_ask: number
    carbon_cost_per_ask: number
  }
  scenario: {
    total_cask: number
    estimated_rask: number
    spread: number
    fuel_cost_per_ask: number
    carbon_cost_per_ask: number
    nav_charges_per_ask: number
    airport_cost_per_ask: number
    crew_cost_per_ask: number
    other_cost_per_ask: number
  }
  deltas: {
    total_cask: number
    estimated_rask: number
    spread: number
    fuel_cost_per_ask: number
    carbon_cost_per_ask: number
  }
  impact_summary: string
  applied_parameters: Record<string, number>
}
