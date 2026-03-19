import type { ApiResponse, StateVector, EnrichedFlight } from '@/types'

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'

async function apiFetch<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`)
  if (!res.ok) throw new Error(`API error ${res.status}: ${path}`)
  return res.json()
}

export const api = {
  getLiveFlights: () =>
    apiFetch<ApiResponse<StateVector[]>>('/flights/live'),

  getFlightHistory: (limit = 100) =>
    apiFetch<ApiResponse<EnrichedFlight[]>>(`/flights/history?limit=${limit}`),

  getFuelAnalytics: () =>
    apiFetch<ApiResponse<unknown[]>>('/analytics/fuel'),

  getNetworkAnalytics: () =>
    apiFetch<ApiResponse<unknown[]>>('/analytics/network'),

  getEmissions: () =>
    apiFetch<ApiResponse<unknown[]>>('/analytics/emissions'),
}
