'use client'

import { useState, useMemo } from 'react'
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, LineChart, Line, CartesianGrid } from 'recharts'
import { api } from '@/lib/api'
import { useApiData } from '@/hooks/useApiData'
import { Card, DataTable, LoadingSpinner, ErrorBanner, StatusBadge } from '@/components/ui'
import { colors, buttonPrimaryStyle, buttonStyle, tooltipStyle } from '@/styles/theme'
import type { FleetAircraft, RoutePerformance } from '@/types'

type PerfCategory = '' | 'overperforming' | 'average' | 'underperforming'

const PERF_COLORS: Record<string, string> = {
  overperforming: colors.green,
  average: colors.orange,
  underperforming: colors.red,
}

function KPICard({ label, value, unit, color }: { label: string; value: string; unit: string; color: string }) {
  return (
    <Card>
      <div style={{ fontSize: 11, color: colors.textMuted, textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 4 }}>
        {label}
      </div>
      <div style={{ fontSize: 24, fontWeight: 700, color }}>{value}</div>
      <div style={{ fontSize: 11, color: colors.textDim }}>{unit}</div>
    </Card>
  )
}

export default function AnalyticsPage() {
  const [computing, setComputing] = useState(false)
  const [perfCategory, setPerfCategory] = useState<PerfCategory>('')

  const kpi = useApiData(() => api.getCurrentKPIs(), { refreshInterval: 60000 })
  const history = useApiData(() => api.getKPIHistory('weekly', 12), { refreshInterval: 60000 })
  const fleet = useApiData(() => api.getFleetUtilization(24), { refreshInterval: 60000 })
  const routePerf = useApiData(
    () => api.getRoutePerformance(perfCategory || undefined, 50),
    { refreshInterval: 120000 },
  )
  const routeFreq = useApiData(() => api.getRouteFrequency())

  const kpiHistory = useMemo(() => [...(history.data ?? [])].reverse(), [history.data])
  const k = kpi.data

  const handleCompute = async () => {
    setComputing(true)
    try {
      await api.triggerKPICompute('weekly')
      kpi.refresh()
      history.refresh()
      fleet.refresh()
    } catch { /* ignore */ }
    setComputing(false)
  }

  const anyError = kpi.error || history.error || fleet.error
  const initialLoading = kpi.loading && history.loading && fleet.loading

  if (initialLoading) return <LoadingSpinner message="Loading KPI data…" />

  return (
    <div style={{ padding: 24, overflowY: 'auto', height: '100%' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
        <h1 style={{ margin: 0, fontSize: 22, color: colors.text }}>SWISS Operational KPIs</h1>
        <button onClick={handleCompute} disabled={computing} style={{ ...buttonPrimaryStyle, opacity: computing ? 0.6 : 1 }}>
          {computing ? 'Computing…' : 'Refresh KPIs'}
        </button>
      </div>

      {anyError && <ErrorBanner message={anyError} onRetry={() => { kpi.refresh(); history.refresh(); fleet.refresh() }} />}

      {/* KPI Cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(180px, 1fr))', gap: 12, marginBottom: 24 }}>
        <KPICard label="Available Seat Km" value={k?.total_ask ? `${(k.total_ask / 1e6).toFixed(1)}M` : '—'} unit="ASK (millions)" color={colors.accent} />
        <KPICard label="Fleet Utilization" value={k?.avg_block_hours_per_day?.toFixed(1) ?? '—'} unit="block hrs/day" color={colors.purple} />
        <KPICard label="Aircraft Tracked" value={k?.unique_aircraft_count?.toString() ?? '—'} unit="unique SWISS aircraft" color={colors.green} />
        <KPICard label="Departures" value={k?.total_departures?.toString() ?? '—'} unit="this period" color={colors.orange} />
        <KPICard label="Routes" value={k?.unique_routes?.toString() ?? '—'} unit="unique routes" color={colors.accent} />
        <KPICard label="Avg Turnaround" value={k?.avg_turnaround_min?.toFixed(0) ?? '—'} unit="minutes" color="#fb923c" />
        <KPICard label="Fuel per ASK" value={k?.fuel_burn_per_ask?.toFixed(2) ?? '—'} unit="g/ASK" color={colors.red} />
        <KPICard label="Load Factor" value={k?.estimated_load_factor ? `${(k.estimated_load_factor * 100).toFixed(0)}%` : '—'} unit="estimated" color={colors.cyan} />
      </div>

      {/* Charts Row */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(400px, 1fr))', gap: 16, marginBottom: 24 }}>
        <Card title="ASK Trend (Weekly)">
          <ResponsiveContainer width="100%" height={220}>
            <LineChart data={kpiHistory}>
              <CartesianGrid strokeDasharray="3 3" stroke={colors.border} />
              <XAxis dataKey="period_start" tick={{ fontSize: 10, fill: colors.textMuted }}
                tickFormatter={v => new Date(v).toLocaleDateString('en', { month: 'short', day: 'numeric' })} />
              <YAxis tick={{ fontSize: 10, fill: colors.textMuted }} tickFormatter={v => `${(v / 1e6).toFixed(1)}M`} />
              <Tooltip contentStyle={tooltipStyle} formatter={(v: number) => `${(v / 1e6).toFixed(2)}M`} />
              <Line type="monotone" dataKey="total_ask" stroke={colors.accent} strokeWidth={2} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </Card>

        <Card title="Fleet Utilization Trend">
          <ResponsiveContainer width="100%" height={220}>
            <LineChart data={kpiHistory}>
              <CartesianGrid strokeDasharray="3 3" stroke={colors.border} />
              <XAxis dataKey="period_start" tick={{ fontSize: 10, fill: colors.textMuted }}
                tickFormatter={v => new Date(v).toLocaleDateString('en', { month: 'short', day: 'numeric' })} />
              <YAxis tick={{ fontSize: 10, fill: colors.textMuted }} />
              <Tooltip contentStyle={tooltipStyle} />
              <Line type="monotone" dataKey="avg_block_hours_per_day" stroke={colors.purple} strokeWidth={2} dot={false} name="Hrs/Day" />
            </LineChart>
          </ResponsiveContainer>
        </Card>
      </div>

      {/* Fleet Activity Table */}
      <Card title="SWISS Fleet Activity (Last 24h)" style={{ marginBottom: 24 }}>
        <DataTable<FleetAircraft & Record<string, unknown>>
          columns={[
            { key: 'icao24', label: 'ICAO24', render: r => <span style={{ fontFamily: 'monospace' }}>{r.icao24}</span> },
            { key: 'callsign', label: 'Callsign' },
            { key: 'block_hours', label: 'Block Hours', align: 'right', render: r => r.block_hours != null ? <span style={{ color: colors.purple }}>{Number(r.block_hours).toFixed(1)}</span> : '—' },
            { key: 'observations', label: 'Observations', align: 'right' },
            { key: 'first_seen', label: 'First Seen', render: r => r.first_seen ? new Date(r.first_seen as string).toLocaleTimeString() : '—' },
            { key: 'last_seen', label: 'Last Seen', render: r => r.last_seen ? new Date(r.last_seen as string).toLocaleTimeString() : '—' },
            { key: 'avg_fuel', label: 'Avg Fuel (kg/s)', align: 'right', render: r => r.avg_fuel != null ? <span style={{ color: colors.orange }}>{Number(r.avg_fuel).toFixed(3)}</span> : '—' },
          ]}
          data={(fleet.data ?? []) as (FleetAircraft & Record<string, unknown>)[]}
          emptyMessage="No SWISS fleet data available yet. KPIs will populate as ADS-B data accumulates."
          maxRows={20}
        />
      </Card>

      {/* Route Frequency */}
      {routeFreq.data && routeFreq.data.length > 0 && (
        <Card title="Top Routes by Flight Count" style={{ marginBottom: 24 }}>
          <ResponsiveContainer width="100%" height={Math.min(400, routeFreq.data.length * 28 + 40)}>
            <BarChart data={routeFreq.data.slice(0, 15)} layout="vertical" margin={{ left: 80 }}>
              <CartesianGrid strokeDasharray="3 3" stroke={colors.border} />
              <XAxis type="number" tick={{ fontSize: 10, fill: colors.textMuted }} />
              <YAxis
                type="category"
                dataKey={(d: Record<string, unknown>) => `${d.origin_icao}→${d.destination_icao}`}
                tick={{ fontSize: 11, fill: colors.textMuted }}
                width={80}
              />
              <Tooltip contentStyle={tooltipStyle} />
              <Bar dataKey="flight_count" fill={colors.accent} radius={[0, 4, 4, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </Card>
      )}

      {/* Route Performance */}
      <Card title="Route Performance" style={{ marginBottom: 24 }}>
        <div style={{ display: 'flex', gap: 6, marginBottom: 12 }}>
          {([['', 'All'], ['overperforming', 'Overperforming'], ['average', 'Average'], ['underperforming', 'Underperforming']] as [PerfCategory, string][]).map(([cat, label]) => (
            <button
              key={cat}
              onClick={() => setPerfCategory(cat)}
              style={{
                ...buttonStyle,
                background: perfCategory === cat ? colors.accent : colors.card,
                color: perfCategory === cat ? colors.bg : colors.text,
                fontWeight: perfCategory === cat ? 600 : 400,
              }}
            >
              {label}
            </button>
          ))}
          <button
            onClick={async () => { await api.triggerRoutePerformanceCompute(); routePerf.refresh() }}
            style={{ ...buttonStyle, marginLeft: 'auto', fontSize: 12 }}
          >
            Recompute
          </button>
        </div>

        {routePerf.error && <ErrorBanner message={routePerf.error} onRetry={routePerf.refresh} />}

        <DataTable<RoutePerformance & Record<string, unknown>>
          columns={[
            { key: 'route', label: 'Route', render: r => `${r.origin_icao} → ${r.destination_icao}` },
            { key: 'total_flights', label: 'Flights', align: 'right' },
            { key: 'baseline_duration_min', label: 'Baseline (min)', align: 'right', render: r => r.baseline_duration_min?.toFixed(0) ?? '—' },
            { key: 'recent_duration_min', label: 'Recent (min)', align: 'right', render: r => r.recent_duration_min?.toFixed(0) ?? '—' },
            {
              key: 'duration_deviation_pct', label: 'Duration Δ%', align: 'right',
              render: r => {
                const v = r.duration_deviation_pct
                if (v == null) return '—'
                const c = v > 0 ? colors.red : v < 0 ? colors.green : colors.text
                return <span style={{ color: c }}>{v > 0 ? '+' : ''}{v.toFixed(1)}%</span>
              },
            },
            {
              key: 'fuel_deviation_pct', label: 'Fuel Δ%', align: 'right',
              render: r => {
                const v = r.fuel_deviation_pct
                if (v == null) return '—'
                const c = v > 0 ? colors.red : v < 0 ? colors.green : colors.text
                return <span style={{ color: c }}>{v > 0 ? '+' : ''}{v.toFixed(1)}%</span>
              },
            },
            { key: 'performance_score', label: 'Score', align: 'right', render: r => r.performance_score?.toFixed(1) ?? '—' },
            {
              key: 'category', label: 'Category',
              render: r => <StatusBadge label={r.category} color={PERF_COLORS[r.category] ?? colors.textMuted} />,
            },
          ]}
          data={(routePerf.data ?? []) as (RoutePerformance & Record<string, unknown>)[]}
          emptyMessage="No route performance data. Run route performance computation first."
          maxRows={50}
        />
      </Card>
    </div>
  )
}
