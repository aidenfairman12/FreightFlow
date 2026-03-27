/**
 * Static data loaders — all data is pre-computed from FAF5 2022 and
 * served as JSON from /public/data. No backend required.
 */
import type {
  Product,
  RiskScore,
  SupplyChainData,
  ZoneInfo,
  CriticalNode,
} from '@/types'

const BASE = '/data'

async function loadJson<T>(file: string): Promise<T> {
  const res = await fetch(`${BASE}/${file}`)
  if (!res.ok) throw new Error(`Failed to load ${file}: ${res.status}`)
  return res.json() as Promise<T>
}

export const data = {
  products:       () => loadJson<Product[]>('products.json'),
  riskScores:     () => loadJson<RiskScore[]>('risk_scores.json'),
  zones:          () => loadJson<Record<string, ZoneInfo>>('zones.json'),
  supplyChain:    (sctg2: string) => loadJson<SupplyChainData>(`supply_chain_${sctg2}.json`),
  criticalNodes:  () => loadJson<CriticalNode[]>('critical_nodes.json'),
}
