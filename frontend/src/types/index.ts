// ── Static JSON data shapes (pre-computed from FAF5 2022 data) ────────────

export interface ZoneInfo {
  name: string
  state: string
  lat: number
  lon: number
  type: 'metro' | 'rest_of_state' | string
}

export interface ProductPrecursor {
  sctg2: string
  name: string
  ratio: number
  role: string
}

export interface Product {
  sctg2: string
  name: string
  description: string
  precursors: ProductPrecursor[]
}

export interface RiskSourceZone {
  zone_id: number
  zone_name: string
  state: string
  tons_k: number
  pct: number
}

export interface RiskScore {
  sctg2: string
  name: string
  concentration_top3: number
  concentration_top5: number
  risk_tier: 'critical' | 'high' | 'medium' | 'low'
  top_assembly_zone: string
  primary_precursor: string
  total_precursor_tons_k: number
  top_source_zones: RiskSourceZone[]
  num_source_zones: number
}

export interface SourceZone {
  zone_id: number
  zone_name: string
  state: string
  latitude: number
  longitude: number
  tons_k: number
  value_m: number
  tmiles_m: number
  pct_of_precursor: number
  primary_mode: string
  est_cost_usd: number
}

export interface ModeSplit {
  mode: string
  pct: number
}

export interface PrecursorDetail {
  sctg2: string
  name: string
  role: string
  ratio: number
  total_tons_k: number
  total_value_m: number
  total_tmiles_m: number
  est_cost_usd: number
  primary_mode: string
  mode_split: ModeSplit[]
  num_sources: number
  sources: SourceZone[]
}

export interface AssemblyZoneData {
  zone_id: number
  zone_name: string
  state: string
  latitude: number
  longitude: number
  total_precursor_tons_k: number
  total_est_cost_usd: number
  precursors: PrecursorDetail[]
}

export interface SupplyChainData {
  sctg2: string
  name: string
  description: string
  year: number
  assembly_zones: AssemblyZoneData[]
}

// ── Disruption simulation (computed client-side) ──────────────────────────

// ── Critical Nodes (pre-computed cross-product systemic risk) ─────────────

export interface CriticalNodeProduct {
  sctg2: string
  product_name: string
  precursor_name: string
  precursor_sctg2: string
  tons_k: number
  pct_of_precursor: number   // fraction of that precursor's supply from this zone
  pct_of_product: number     // fraction of that product's total precursor weight
}

export interface CriticalNode {
  rank: number
  zone_id: number
  zone_name: string
  state: string
  lat: number
  lon: number
  total_tons_k: number
  total_cost_usd: number
  systemic_score: number      // fraction of all modelled precursor tons across products
  products_affected: CriticalNodeProduct[]
}

// ── Disruption simulation (computed client-side) ──────────────────────────

export interface DisruptedPrecursor {
  name: string
  sctg2: string
  tons_k: number          // tonnage gap for this precursor
  pct_of_precursor: number  // fraction of that precursor's total supply lost
}

export interface DisruptionResult {
  disrupted_zone_ids:   number[]
  disrupted_zone_names: string[]
  tonnage_gap_k:        number
  cost_impact_usd:      number
  pct_of_total:         number   // gap / all-precursor total
  per_precursor:        DisruptedPrecursor[]
}
