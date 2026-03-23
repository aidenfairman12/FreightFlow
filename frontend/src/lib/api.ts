import type {
  ApiResponse, FafZone, Corridor, CorridorCostData,
  FreightKPI, FreightUnitEconomics, EconomicFactors, CostBreakdown,
  ModeComparison, ScenarioPreset, Scenario, ScenarioResults,
} from '@/types'

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'

async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, options)
  if (!res.ok) throw new Error(`API error ${res.status}: ${path}`)
  return res.json()
}

export const api = {
  // ── Corridors ──────────────────────────────────────────────────────────
  getCorridors: () =>
    apiFetch<ApiResponse<Corridor[]>>('/corridors/'),

  getCorridorFlows: (corridorId: string, year = 2022, commodity?: string) =>
    apiFetch<ApiResponse<Record<string, unknown>[]>>(
      `/corridors/${corridorId}/flows?year=${year}${commodity ? `&commodity=${commodity}` : ''}`,
    ),

  getCorridorModes: (corridorId: string, year = 2022) =>
    apiFetch<ApiResponse<CorridorCostData>>(`/corridors/${corridorId}/modes?year=${year}`),

  getCorridorTrends: (corridorId: string) =>
    apiFetch<ApiResponse<Record<string, unknown>[]>>(`/corridors/${corridorId}/trends`),

  // ── Flows ──────────────────────────────────────────────────────────────
  queryFlows: (params: { year?: number; commodity?: string; mode?: number; origin?: number; dest?: number; limit?: number } = {}) => {
    const sp = new URLSearchParams()
    if (params.year) sp.set('year', String(params.year))
    if (params.commodity) sp.set('commodity', params.commodity)
    if (params.mode) sp.set('mode', String(params.mode))
    if (params.origin) sp.set('origin', String(params.origin))
    if (params.dest) sp.set('dest', String(params.dest))
    if (params.limit) sp.set('limit', String(params.limit))
    return apiFetch<ApiResponse<Record<string, unknown>[]>>(`/flows/?${sp}`)
  },

  getTopCorridors: (year = 2022, commodity?: string, limit = 20) =>
    apiFetch<ApiResponse<Record<string, unknown>[]>>(
      `/flows/top-corridors?year=${year}${commodity ? `&commodity=${commodity}` : ''}&limit=${limit}`,
    ),

  getModeTrends: (commodity?: string) =>
    apiFetch<ApiResponse<Record<string, unknown>[]>>(
      `/flows/mode-trends${commodity ? `?commodity=${commodity}` : ''}`,
    ),

  getZones: () =>
    apiFetch<ApiResponse<FafZone[]>>('/flows/zones'),

  // ── Analytics ──────────────────────────────────────────────────────────
  getCorridorPerformance: (sortBy = 'estimated_cost', limit = 50) =>
    apiFetch<ApiResponse<Record<string, unknown>[]>>(
      `/analytics/corridor-performance?sort_by=${sortBy}&limit=${limit}`,
    ),

  getModeComparison: (year = 2022) =>
    apiFetch<ApiResponse<ModeComparison[]>>(`/analytics/mode-comparison?year=${year}`),

  getCommoditySummary: (year = 2022, limit = 20) =>
    apiFetch<ApiResponse<Record<string, unknown>[]>>(`/analytics/commodity-summary?year=${year}&limit=${limit}`),

  triggerCorridorPerformanceCompute: (year = 2022) =>
    apiFetch<ApiResponse<{ corridors_scored: number }>>(`/analytics/corridor-performance/compute?year=${year}`, { method: 'POST' }),

  // ── KPI ────────────────────────────────────────────────────────────────
  getCurrentKPIs: (scope = 'national') =>
    apiFetch<ApiResponse<FreightKPI | null>>(`/kpi/current?scope=${scope}`),

  getKPIHistory: (scope = 'national', limit = 20) =>
    apiFetch<ApiResponse<FreightKPI[]>>(`/kpi/history?scope=${scope}&limit=${limit}`),

  getModeShare: () =>
    apiFetch<ApiResponse<Record<string, unknown>[]>>('/kpi/mode-share'),

  triggerKPICompute: (year = 2022, scope = 'national') =>
    apiFetch<ApiResponse<FreightKPI | null>>(`/kpi/compute?year=${year}&scope=${scope}`, { method: 'POST' }),

  // ── Economics ──────────────────────────────────────────────────────────
  getLatestEconomicFactors: () =>
    apiFetch<ApiResponse<EconomicFactors>>('/economics/latest'),

  getFactorHistory: (factorName: string, days = 90) =>
    apiFetch<ApiResponse<unknown[]>>(`/economics/history/${factorName}?days=${days}`),

  getCurrentUnitEconomics: () =>
    apiFetch<ApiResponse<FreightUnitEconomics | null>>('/economics/unit-economics/current'),

  getUnitEconomicsHistory: (limit = 20) =>
    apiFetch<ApiResponse<FreightUnitEconomics[]>>(`/economics/unit-economics/history?limit=${limit}`),

  getCostBreakdown: () =>
    apiFetch<ApiResponse<CostBreakdown | null>>('/economics/cost-breakdown'),

  refreshEconomicData: () =>
    apiFetch<ApiResponse<EconomicFactors>>('/economics/refresh', { method: 'POST' }),

  // ── Scenarios ──────────────────────────────────────────────────────────
  getScenarioPresets: () =>
    apiFetch<ApiResponse<ScenarioPreset[]>>('/scenarios/presets/list'),

  listScenarios: (limit = 20) =>
    apiFetch<ApiResponse<Scenario[]>>(`/scenarios/?limit=${limit}`),

  getScenario: (id: string) =>
    apiFetch<ApiResponse<Scenario>>(`/scenarios/${id}`),

  createScenario: (body: { name: string; description?: string; parameters: Record<string, number> }) =>
    apiFetch<ApiResponse<ScenarioResults>>('/scenarios/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    }),

  deleteScenario: (id: string) =>
    apiFetch<ApiResponse<unknown>>(`/scenarios/${id}`, { method: 'DELETE' }),
}
