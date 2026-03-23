// ── Core ──────────────────────────────────────────────────────────────────

export interface ApiResponse<T> {
  data: T
  error: string | null
  meta: Record<string, unknown>
}

// ── FAF5 Reference Data ──────────────────────────────────────────────────

export interface FafZone {
  zone_id: number
  zone_name: string
  state_name: string | null
  latitude: number | null
  longitude: number | null
  zone_type: string | null
}

export interface Commodity {
  sctg2: string
  commodity_name: string
  commodity_group: string | null
}

// ── Freight Flows ────────────────────────────────────────────────────────

export interface FreightFlow {
  origin_zone_id: number
  origin_name: string | null
  dest_zone_id: number
  dest_name: string | null
  sctg2: string
  commodity_name: string | null
  mode_code: number
  mode_name: string
  year: number
  tons_thousands: number | null
  value_millions: number | null
  ton_miles_millions: number | null
}

// ── Corridors ────────────────────────────────────────────────────────────

export interface Corridor {
  corridor_id: string
  name: string
  description: string | null
  origin_zones: number[]
  dest_zones: number[]
  origin_lat: number | null
  origin_lon: number | null
  dest_lat: number | null
  dest_lon: number | null
  // Performance data (from JOIN)
  year?: number
  total_tons?: number | null
  total_value_usd?: number | null
  total_ton_miles?: number | null
  mode_breakdown?: Record<string, unknown> | null
  estimated_cost?: number | null
  cost_per_ton?: number | null
}

export interface CorridorCostData {
  corridor_id: string
  year: number
  commodity: string | null
  total_estimated_cost: number
  modes: {
    mode_code: number
    mode_name: string
    tons_thousands: number | null
    value_millions: number | null
    ton_miles_millions: number | null
    total_cost_usd: number
    cost_per_ton_mile: number
    cost_per_ton: number
    components: Record<string, number>
  }[]
}

// ── Freight KPIs ─────────────────────────────────────────────────────────

export interface FreightKPI {
  id: string
  period_year: number
  scope: string
  total_tons: number | null
  total_value_usd: number | null
  total_ton_miles: number | null
  truck_share_pct: number | null
  rail_share_pct: number | null
  air_share_pct: number | null
  water_share_pct: number | null
  multi_share_pct: number | null
  avg_cost_per_ton_mile: number | null
  total_estimated_cost: number | null
  value_per_ton: number | null
  ton_miles_per_ton: number | null
}

// ── Economics ────────────────────────────────────────────────────────────

export interface EconomicFactors {
  [key: string]: {
    value: number
    unit: string
    source: string
    date: string
  }
}

export interface CostBreakdown {
  components: {
    fuel: number
    labor: number
    equipment: number
    insurance: number
    tolls_fees: number
    other: number
  }
  total_cost_per_tm: number
  year: number
}

export interface FreightUnitEconomics {
  id: string
  year: number
  scope: string
  fuel_cost_per_tm: number | null
  labor_cost_per_tm: number | null
  equipment_cost_per_tm: number | null
  insurance_cost_per_tm: number | null
  tolls_fees_per_tm: number | null
  other_cost_per_tm: number | null
  total_cost_per_tm: number | null
  revenue_per_tm: number | null
  margin_per_tm: number | null
}

// ── Mode Comparison ──────────────────────────────────────────────────────

export interface ModeComparison {
  mode_code: number
  mode_name: string
  total_tons_thousands: number | null
  total_value_millions: number | null
  total_ton_miles_millions: number | null
  cost_per_ton_mile: number
  total_estimated_cost: number
  source: string
}

// ── Scenarios ────────────────────────────────────────────────────────────

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
    total_cost_per_tm: number
    fuel: number
    labor: number
    equipment: number
    insurance: number
    tolls_fees: number
    other: number
    revenue_per_tm: number
    margin_per_tm: number
  }
  scenario: {
    total_cost_per_tm: number
    fuel: number
    labor: number
    equipment: number
    insurance: number
    tolls_fees: number
    other: number
    carbon_tax: number
    congestion_cost: number
    mode_shift_savings: number
    revenue_per_tm: number
    margin_per_tm: number
  }
  deltas: {
    total_cost_per_tm: number
    fuel: number
    labor: number
    tolls_fees: number
    margin_per_tm: number
    cost_change_pct: number
  }
  impact_summary: string
  applied_parameters: Record<string, number>
}
