import type {
  ApiResponse, StateVector, EnrichedFlight, OperationalKPI,
  FleetAircraft, EconomicFactors, CASKBreakdown, UnitEconomics,
  FeatureImportance, Prediction, FuelAnomaly, RouteProfitability,
  ScenarioPreset, Scenario, RoutePerformance, FlightDeviation,
  SchedulePattern, ImputedFlight, MLModel,
} from '@/types'

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'

async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, options)
  if (!res.ok) throw new Error(`API error ${res.status}: ${path}`)
  return res.json()
}

export const api = {
  // ── Flights (Phase 1-2) ──────────────────────────────────────────────────
  getLiveFlights: () =>
    apiFetch<ApiResponse<StateVector[]>>('/flights/live'),

  getFlightHistory: (limit = 100) =>
    apiFetch<ApiResponse<EnrichedFlight[]>>(`/flights/history?limit=${limit}`),

  // ── Analytics (Phase 2) ──────────────────────────────────────────────────
  getFuelAnalytics: () =>
    apiFetch<ApiResponse<unknown[]>>('/analytics/fuel'),

  getNetworkAnalytics: () =>
    apiFetch<ApiResponse<unknown[]>>('/analytics/network'),

  getEmissions: () =>
    apiFetch<ApiResponse<{ aircraft_count: number; total_co2_kg_s: number; total_fuel_kg_s: number }>>('/analytics/emissions'),

  getRoutePerformance: (category?: string, limit = 50) =>
    apiFetch<ApiResponse<RoutePerformance[]>>(
      `/analytics/route-performance?${category ? `category=${category}&` : ''}limit=${limit}`,
    ),

  getFlightDeviations: (origin?: string, destination?: string, limit = 50) =>
    apiFetch<ApiResponse<FlightDeviation[]>>(
      `/analytics/flight-deviations?${new URLSearchParams({
        ...(origin && { origin }),
        ...(destination && { destination }),
        limit: String(limit),
      })}`,
    ),

  triggerRoutePerformanceCompute: () =>
    apiFetch<ApiResponse<{ routes_scored: number }>>('/analytics/route-performance/compute', { method: 'POST' }),

  // ── KPI (Phase 5) ───────────────────────────────────────────────────────
  getCurrentKPIs: () =>
    apiFetch<ApiResponse<OperationalKPI | null>>('/kpi/current'),

  getKPIHistory: (periodType = 'weekly', limit = 52) =>
    apiFetch<ApiResponse<OperationalKPI[]>>(`/kpi/history?period_type=${periodType}&limit=${limit}`),

  getFleetUtilization: (hours = 24) =>
    apiFetch<ApiResponse<FleetAircraft[]>>(`/kpi/fleet?hours=${hours}`),

  getRouteFrequency: () =>
    apiFetch<ApiResponse<unknown[]>>('/kpi/routes'),

  triggerKPICompute: (periodType = 'weekly') =>
    apiFetch<ApiResponse<OperationalKPI | null>>(`/kpi/compute?period_type=${periodType}`, { method: 'POST' }),

  // ── Economics (Phase 6-7) ────────────────────────────────────────────────
  getLatestEconomicFactors: () =>
    apiFetch<ApiResponse<EconomicFactors>>('/economics/latest'),

  getFactorHistory: (factorName: string, days = 90) =>
    apiFetch<ApiResponse<unknown[]>>(`/economics/history/${factorName}?days=${days}`),

  getCurrentUnitEconomics: () =>
    apiFetch<ApiResponse<UnitEconomics | null>>('/economics/unit-economics/current'),

  getUnitEconomicsHistory: (limit = 52) =>
    apiFetch<ApiResponse<UnitEconomics[]>>(`/economics/unit-economics/history?limit=${limit}`),

  getCASKBreakdown: () =>
    apiFetch<ApiResponse<CASKBreakdown | null>>('/economics/cask-breakdown'),

  refreshEconomicData: () =>
    apiFetch<ApiResponse<EconomicFactors>>('/economics/refresh', { method: 'POST' }),

  // ── Predictions (Phase 8) ────────────────────────────────────────────────
  getFeatureImportance: (modelName = 'cask_feature_importance') =>
    apiFetch<ApiResponse<FeatureImportance[]>>(`/predictions/feature-importance?model_name=${modelName}`),

  getForecasts: (target = 'total_cask', limit = 10) =>
    apiFetch<ApiResponse<Prediction[]>>(`/predictions/forecasts?target=${target}&limit=${limit}`),

  getFuelAnomalies: (hours = 24) =>
    apiFetch<ApiResponse<FuelAnomaly[]>>(`/predictions/anomalies?hours=${hours}`),

  getRouteProfitability: () =>
    apiFetch<ApiResponse<RouteProfitability[]>>('/predictions/route-profitability'),

  triggerMLTraining: () =>
    apiFetch<ApiResponse<unknown>>('/predictions/train', { method: 'POST' }),

  // ── Scenarios (Phase 9) ──────────────────────────────────────────────────
  getScenarioPresets: () =>
    apiFetch<ApiResponse<ScenarioPreset[]>>('/scenarios/presets/list'),

  listScenarios: (limit = 20) =>
    apiFetch<ApiResponse<Scenario[]>>(`/scenarios/?limit=${limit}`),

  getScenario: (id: string) =>
    apiFetch<ApiResponse<Scenario>>(`/scenarios/${id}`),

  createScenario: (body: { name: string; description?: string; parameters: Record<string, number> }) =>
    apiFetch<ApiResponse<unknown>>('/scenarios/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    }),

  deleteScenario: (id: string) =>
    apiFetch<ApiResponse<unknown>>(`/scenarios/${id}`, { method: 'DELETE' }),

  // ── Schedule ─────────────────────────────────────────────────────────────
  getSchedulePatterns: () =>
    apiFetch<ApiResponse<SchedulePattern[]>>('/schedule/patterns'),

  getImputedFlights: (status?: string, limit = 100) =>
    apiFetch<ApiResponse<ImputedFlight[]>>(
      `/schedule/imputed?${new URLSearchParams({
        ...(status && { status }),
        limit: String(limit),
      })}`,
    ),

  triggerImputationCycle: () =>
    apiFetch<ApiResponse<unknown>>('/schedule/run', { method: 'POST' }),

  // ── ML Models ────────────────────────────────────────────────────────────
  getMLModels: () =>
    apiFetch<ApiResponse<MLModel[]>>('/predictions/models'),
}
