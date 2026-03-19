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
