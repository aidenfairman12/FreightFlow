'use client'

import { useState, useMemo } from 'react'
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  CartesianGrid, Area, AreaChart, Line,
} from 'recharts'
import { api } from '@/lib/api'
import { useApiData } from '@/hooks/useApiData'
import { Card, DataTable, LoadingSpinner, ErrorBanner, StatusBadge, EmptyState } from '@/components/ui'
import { colors, buttonPrimaryStyle, tooltipStyle } from '@/styles/theme'
import type { FuelAnomaly, RouteProfitability, MLModel } from '@/types'

const PROFITABILITY_COLORS: Record<string, string> = {
  profitable: colors.green,
  marginal: colors.orange,
  unprofitable: colors.red,
}

export default function PredictionsPage() {
  const [training, setTraining] = useState(false)

  const features = useApiData(() => api.getFeatureImportance())
  const forecastsRaw = useApiData(() => api.getForecasts('total_cask', 12))
  const anomalies = useApiData(() => api.getFuelAnomalies(24))
  const routes = useApiData(() => api.getRouteProfitability())
  const models = useApiData(() => api.getMLModels())

  const forecasts = useMemo(() => [...(forecastsRaw.data ?? [])].reverse(), [forecastsRaw.data])

  const handleTrain = async () => {
    setTraining(true)
    try {
      await api.triggerMLTraining()
      features.refresh()
      forecastsRaw.refresh()
      anomalies.refresh()
      routes.refresh()
      models.refresh()
    } catch { /* ignore */ }
    setTraining(false)
  }

  const anyError = features.error || forecastsRaw.error || anomalies.error || routes.error
  const initialLoading = features.loading && forecastsRaw.loading && anomalies.loading && routes.loading

  if (initialLoading) return <LoadingSpinner message="Loading ML data…" />

  return (
    <div style={{ padding: 24, overflowY: 'auto', height: '100%' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
        <h1 style={{ margin: 0, fontSize: 22, color: colors.text }}>ML Predictions & Analytics</h1>
        <button onClick={handleTrain} disabled={training} style={{ ...buttonPrimaryStyle, background: colors.purple, borderColor: colors.purple, opacity: training ? 0.6 : 1 }}>
          {training ? 'Training…' : 'Train Models'}
        </button>
      </div>

      {anyError && <ErrorBanner message={anyError} onRetry={() => { features.refresh(); forecastsRaw.refresh(); anomalies.refresh(); routes.refresh() }} />}

      {/* Trained Models */}
      {models.data && models.data.length > 0 && (
        <Card title="Trained Models" style={{ marginBottom: 24 }}>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 10 }}>
            {models.data.map(m => (
              <div key={m.model_name} style={{ background: colors.bg, borderRadius: 6, padding: 12 }}>
                <div style={{ fontWeight: 600, fontSize: 13, color: colors.text, marginBottom: 4 }}>{m.model_name}</div>
                <div style={{ fontSize: 11, color: colors.textMuted }}>
                  v{m.model_version}
                  {m.feature_count != null && ` · ${m.feature_count} features`}
                  {m.prediction_count != null && ` · ${m.prediction_count} predictions`}
                </div>
                <div style={{ fontSize: 10, color: colors.textDim, marginTop: 2 }}>
                  {m.last_trained ? `Trained: ${new Date(m.last_trained).toLocaleDateString()}` : ''}
                </div>
              </div>
            ))}
          </div>
        </Card>
      )}

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(400px, 1fr))', gap: 16, marginBottom: 24 }}>
        {/* Feature Importance */}
        <Card title="CASK Feature Importance">
          {features.data && features.data.length > 0 ? (
            <ResponsiveContainer width="100%" height={280}>
              <BarChart data={features.data.slice(0, 10)} layout="vertical" margin={{ left: 100 }}>
                <XAxis type="number" tick={{ fontSize: 10, fill: colors.textMuted }} />
                <YAxis type="category" dataKey="feature_name" tick={{ fontSize: 11, fill: colors.textMuted }} width={100} />
                <Tooltip contentStyle={tooltipStyle} formatter={(v: number) => v.toFixed(4)} />
                <Bar dataKey="importance_score" fill={colors.purple} radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <EmptyState message='No feature importance data yet. Click "Train Models" after accumulating KPI data.' />
          )}
        </Card>

        {/* CASK Forecast */}
        <Card title="CASK Forecast (with confidence bands)">
          {forecasts.length > 0 ? (
            <ResponsiveContainer width="100%" height={280}>
              <AreaChart data={forecasts}>
                <CartesianGrid strokeDasharray="3 3" stroke={colors.border} />
                <XAxis dataKey="target_period_start" tick={{ fontSize: 10, fill: colors.textMuted }}
                  tickFormatter={v => v ? new Date(v).toLocaleDateString('en', { month: 'short', day: 'numeric' }) : ''} />
                <YAxis tick={{ fontSize: 10, fill: colors.textMuted }} />
                <Tooltip contentStyle={tooltipStyle} />
                <Area type="monotone" dataKey="confidence_upper" stroke="none" fill="#38bdf840" />
                <Area type="monotone" dataKey="confidence_lower" stroke="none" fill={colors.bg} />
                <Line type="monotone" dataKey="predicted_value" stroke={colors.accent} strokeWidth={2} dot />
              </AreaChart>
            </ResponsiveContainer>
          ) : (
            <EmptyState message="No forecasts available. Models need sufficient historical data." />
          )}
        </Card>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(400px, 1fr))', gap: 16 }}>
        {/* Fuel Anomalies */}
        <Card title="Fuel Burn Anomalies (Last 24h)">
          <DataTable<FuelAnomaly & Record<string, unknown>>
            columns={[
              { key: 'callsign', label: 'Callsign' },
              { key: 'icao24', label: 'ICAO24', render: r => <span style={{ fontFamily: 'monospace', fontSize: 11 }}>{r.icao24}</span> },
              { key: 'avg_fuel', label: 'Avg Fuel', render: r => <span style={{ color: colors.orange }}>{r.avg_fuel.toFixed(3)} kg/s</span> },
              {
                key: 'z_score', label: 'Z-Score',
                render: r => (
                  <span style={{ color: Math.abs(r.z_score) > 3 ? colors.red : '#fb923c', fontWeight: 600 }}>
                    {r.z_score.toFixed(2)}
                  </span>
                ),
              },
              { key: 'samples', label: 'Samples', align: 'right' },
            ]}
            data={(anomalies.data ?? []) as (FuelAnomaly & Record<string, unknown>)[]}
            emptyMessage="No fuel anomalies detected. This is a good sign!"
          />
        </Card>

        {/* Route Profitability */}
        <Card title="Route Profitability Scoring">
          <DataTable<RouteProfitability & Record<string, unknown>>
            columns={[
              { key: 'route', label: 'Route', render: r => <span style={{ fontFamily: 'monospace', fontSize: 11 }}>{r.origin_icao} → {r.destination_icao}</span> },
              { key: 'flight_count', label: 'Flights', align: 'right' },
              { key: 'avg_fuel_kg', label: 'Avg Fuel', render: r => r.avg_fuel_kg != null ? `${r.avg_fuel_kg.toFixed(0)} kg` : '—' },
              { key: 'profitability_score', label: 'Score', render: r => <span style={{ fontWeight: 600 }}>{r.profitability_score.toFixed(2)}</span> },
              {
                key: 'category', label: 'Category',
                render: r => <StatusBadge label={r.category} color={PROFITABILITY_COLORS[r.category] ?? colors.textMuted} />,
              },
            ]}
            data={(routes.data ?? []) as (RouteProfitability & Record<string, unknown>)[]}
            emptyMessage="No route data available yet."
            maxRows={15}
          />
        </Card>
      </div>
    </div>
  )
}
