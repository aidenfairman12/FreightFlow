'use client'

import { useState, useMemo } from 'react'
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  CartesianGrid, Area, AreaChart, Line,
} from 'recharts'
import { api } from '@/lib/api'
import { useApiData } from '@/hooks/useApiData'
import { Card, CardHeader, CardTitle, CardContent, DataTable, LoadingSpinner, ErrorBanner, StatusBadge, EmptyState, Button } from '@/components/ui'
import { chartTooltipStyle, chartAxisTick, chartGridStroke, chartColors } from '@/lib/chart-theme'
import type { FuelAnomaly, RouteProfitability, MLModel } from '@/types'

const PROFITABILITY_COLORS: Record<string, string> = {
  profitable: chartColors.green,
  marginal: chartColors.orange,
  unprofitable: chartColors.red,
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
    <div className="h-full overflow-y-auto p-6">
      <div className="mb-5 flex items-center justify-between">
        <h1 className="text-xl font-bold text-foreground">ML Predictions & Analytics</h1>
        <Button onClick={handleTrain} disabled={training} className="bg-purple hover:bg-purple/80">
          {training ? 'Training…' : 'Train Models'}
        </Button>
      </div>

      {anyError && <ErrorBanner message={anyError} onRetry={() => { features.refresh(); forecastsRaw.refresh(); anomalies.refresh(); routes.refresh() }} />}

      {/* Trained Models */}
      {models.data && models.data.length > 0 && (
        <Card className="mb-6">
          <CardHeader><CardTitle>Trained Models</CardTitle></CardHeader>
          <CardContent>
            <div className="grid grid-cols-[repeat(auto-fill,minmax(220px,1fr))] gap-2.5">
              {models.data.map(m => (
                <div key={m.model_name} className="rounded-md bg-background p-3">
                  <div className="mb-1 text-[13px] font-semibold text-foreground">{m.model_name}</div>
                  <div className="text-[11px] text-muted-foreground">
                    v{m.model_version}
                    {m.feature_count != null && ` · ${m.feature_count} features`}
                    {m.prediction_count != null && ` · ${m.prediction_count} predictions`}
                  </div>
                  <div className="mt-0.5 text-[10px] text-muted-foreground/60">
                    {m.last_trained ? `Trained: ${new Date(m.last_trained).toLocaleDateString()}` : ''}
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      <div className="mb-6 grid grid-cols-[repeat(auto-fill,minmax(400px,1fr))] gap-4">
        {/* Feature Importance */}
        <Card>
          <CardHeader><CardTitle>CASK Feature Importance</CardTitle></CardHeader>
          <CardContent>
            {features.data && features.data.length > 0 ? (
              <ResponsiveContainer width="100%" height={280}>
                <BarChart data={features.data.slice(0, 10)} layout="vertical" margin={{ left: 100 }}>
                  <XAxis type="number" tick={chartAxisTick} />
                  <YAxis type="category" dataKey="feature_name" tick={{ fontSize: 11, fill: 'var(--muted-foreground)' }} width={100} />
                  <Tooltip contentStyle={chartTooltipStyle} formatter={(v: number) => v.toFixed(4)} />
                  <Bar dataKey="importance_score" fill={chartColors.purple} radius={[0, 4, 4, 0]} />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <EmptyState message='No feature importance data yet. Click "Train Models" after accumulating KPI data.' />
            )}
          </CardContent>
        </Card>

        {/* CASK Forecast */}
        <Card>
          <CardHeader><CardTitle>CASK Forecast (with confidence bands)</CardTitle></CardHeader>
          <CardContent>
            {forecasts.length > 0 ? (
              <ResponsiveContainer width="100%" height={280}>
                <AreaChart data={forecasts}>
                  <CartesianGrid strokeDasharray="3 3" stroke={chartGridStroke} />
                  <XAxis dataKey="target_period_start" tick={chartAxisTick}
                    tickFormatter={v => v ? new Date(v).toLocaleDateString('en', { month: 'short', day: 'numeric' }) : ''} />
                  <YAxis tick={chartAxisTick} />
                  <Tooltip contentStyle={chartTooltipStyle} />
                  <Area type="monotone" dataKey="confidence_upper" stroke="none" fill="rgba(56, 189, 248, 0.25)" />
                  <Area type="monotone" dataKey="confidence_lower" stroke="none" fill="var(--background)" />
                  <Line type="monotone" dataKey="predicted_value" stroke={chartColors.sky} strokeWidth={2} dot />
                </AreaChart>
              </ResponsiveContainer>
            ) : (
              <EmptyState message="No forecasts available. Models need sufficient historical data." />
            )}
          </CardContent>
        </Card>
      </div>

      <div className="grid grid-cols-[repeat(auto-fill,minmax(400px,1fr))] gap-4">
        {/* Fuel Anomalies */}
        <Card>
          <CardHeader><CardTitle>Fuel Burn Anomalies (Last 24h)</CardTitle></CardHeader>
          <CardContent>
            <DataTable<FuelAnomaly & Record<string, unknown>>
              columns={[
                { key: 'callsign', label: 'Callsign' },
                { key: 'icao24', label: 'ICAO24', render: r => <span className="font-mono text-[11px]">{r.icao24}</span> },
                { key: 'avg_fuel', label: 'Avg Fuel', render: r => <span className="text-warning">{r.avg_fuel.toFixed(3)} kg/s</span> },
                {
                  key: 'z_score', label: 'Z-Score',
                  render: r => (
                    <span className={`font-semibold ${Math.abs(r.z_score) > 3 ? 'text-danger' : 'text-warning'}`}>
                      {r.z_score.toFixed(2)}
                    </span>
                  ),
                },
                { key: 'samples', label: 'Samples', align: 'right' },
              ]}
              data={(anomalies.data ?? []) as (FuelAnomaly & Record<string, unknown>)[]}
              emptyMessage="No fuel anomalies detected. This is a good sign!"
            />
          </CardContent>
        </Card>

        {/* Route Profitability */}
        <Card>
          <CardHeader><CardTitle>Route Profitability Scoring</CardTitle></CardHeader>
          <CardContent>
            <DataTable<RouteProfitability & Record<string, unknown>>
              columns={[
                { key: 'route', label: 'Route', render: r => <span className="font-mono text-[11px]">{r.origin_icao} → {r.destination_icao}</span> },
                { key: 'flight_count', label: 'Flights', align: 'right' },
                { key: 'avg_fuel_kg', label: 'Avg Fuel', render: r => r.avg_fuel_kg != null ? `${r.avg_fuel_kg.toFixed(0)} kg` : '—' },
                { key: 'profitability_score', label: 'Score', render: r => <span className="font-semibold">{r.profitability_score.toFixed(2)}</span> },
                {
                  key: 'category', label: 'Category',
                  render: r => <StatusBadge label={r.category} color={PROFITABILITY_COLORS[r.category] ?? '#94a3b8'} />,
                },
              ]}
              data={(routes.data ?? []) as (RouteProfitability & Record<string, unknown>)[]}
              emptyMessage="No route data available yet."
              maxRows={15}
            />
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
