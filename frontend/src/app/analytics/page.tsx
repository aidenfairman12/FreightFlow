'use client'

import { useState, useMemo } from 'react'
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, LineChart, Line, CartesianGrid } from 'recharts'
import { api } from '@/lib/api'
import { useApiData } from '@/hooks/useApiData'
import { Card, CardHeader, CardTitle, CardContent, DataTable, LoadingSpinner, ErrorBanner, StatusBadge, Button } from '@/components/ui'
import { chartTooltipStyle, chartAxisTick, chartGridStroke, chartColors } from '@/lib/chart-theme'
import type { FleetAircraft, RoutePerformance } from '@/types'

type PerfCategory = '' | 'overperforming' | 'average' | 'underperforming'

const PERF_COLORS: Record<string, string> = {
  overperforming: chartColors.green,
  average: chartColors.orange,
  underperforming: chartColors.red,
}

function KPICard({ label, value, unit, color }: { label: string; value: string; unit: string; color: string }) {
  return (
    <Card>
      <CardContent className="pt-4">
        <div className="mb-1 text-[11px] font-medium uppercase tracking-wider text-muted-foreground">
          {label}
        </div>
        <div className="text-2xl font-bold" style={{ color }}>{value}</div>
        <div className="text-[11px] text-muted-foreground">{unit}</div>
      </CardContent>
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
    <div className="h-full overflow-y-auto p-6">
      <div className="mb-5 flex items-center justify-between">
        <h1 className="text-xl font-bold text-foreground">SWISS Operational KPIs</h1>
        <Button onClick={handleCompute} disabled={computing}>
          {computing ? 'Computing…' : 'Refresh KPIs'}
        </Button>
      </div>

      {anyError && <ErrorBanner message={anyError} onRetry={() => { kpi.refresh(); history.refresh(); fleet.refresh() }} />}

      {/* KPI Cards */}
      <div className="mb-6 grid grid-cols-[repeat(auto-fill,minmax(180px,1fr))] gap-3">
        <KPICard label="Available Seat Km" value={k?.total_ask ? `${(k.total_ask / 1e6).toFixed(1)}M` : '—'} unit="ASK (millions)" color={chartColors.sky} />
        <KPICard label="Fleet Utilization" value={k?.avg_block_hours_per_day?.toFixed(1) ?? '—'} unit="block hrs/day" color={chartColors.purple} />
        <KPICard label="Aircraft Tracked" value={k?.unique_aircraft_count?.toString() ?? '—'} unit="unique SWISS aircraft" color={chartColors.green} />
        <KPICard label="Departures" value={k?.total_departures?.toString() ?? '—'} unit="this period" color={chartColors.orange} />
        <KPICard label="Routes" value={k?.unique_routes?.toString() ?? '—'} unit="unique routes" color={chartColors.sky} />
        <KPICard label="Avg Turnaround" value={k?.avg_turnaround_min?.toFixed(0) ?? '—'} unit="minutes" color="#fb923c" />
        <KPICard label="Fuel per ASK" value={k?.fuel_burn_per_ask?.toFixed(2) ?? '—'} unit="g/ASK" color={chartColors.red} />
        <KPICard label="Load Factor" value={k?.estimated_load_factor ? `${(k.estimated_load_factor * 100).toFixed(0)}%` : '—'} unit="estimated" color={chartColors.cyan} />
      </div>

      {/* Charts Row */}
      <div className="mb-6 grid grid-cols-[repeat(auto-fill,minmax(400px,1fr))] gap-4">
        <Card>
          <CardHeader><CardTitle>ASK Trend (Weekly)</CardTitle></CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={220}>
              <LineChart data={kpiHistory}>
                <CartesianGrid strokeDasharray="3 3" stroke={chartGridStroke} />
                <XAxis dataKey="period_start" tick={chartAxisTick}
                  tickFormatter={v => new Date(v).toLocaleDateString('en', { month: 'short', day: 'numeric' })} />
                <YAxis tick={chartAxisTick} tickFormatter={v => `${(v / 1e6).toFixed(1)}M`} />
                <Tooltip contentStyle={chartTooltipStyle} formatter={(v: number) => `${(v / 1e6).toFixed(2)}M`} />
                <Line type="monotone" dataKey="total_ask" stroke={chartColors.sky} strokeWidth={2} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        <Card>
          <CardHeader><CardTitle>Fleet Utilization Trend</CardTitle></CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={220}>
              <LineChart data={kpiHistory}>
                <CartesianGrid strokeDasharray="3 3" stroke={chartGridStroke} />
                <XAxis dataKey="period_start" tick={chartAxisTick}
                  tickFormatter={v => new Date(v).toLocaleDateString('en', { month: 'short', day: 'numeric' })} />
                <YAxis tick={chartAxisTick} />
                <Tooltip contentStyle={chartTooltipStyle} />
                <Line type="monotone" dataKey="avg_block_hours_per_day" stroke={chartColors.purple} strokeWidth={2} dot={false} name="Hrs/Day" />
              </LineChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </div>

      {/* Fleet Activity Table */}
      <Card className="mb-6">
        <CardHeader><CardTitle>SWISS Fleet Activity (Last 24h)</CardTitle></CardHeader>
        <CardContent>
          <DataTable<FleetAircraft & Record<string, unknown>>
            columns={[
              { key: 'icao24', label: 'ICAO24', render: r => <span className="font-mono">{r.icao24}</span> },
              { key: 'callsign', label: 'Callsign' },
              { key: 'block_hours', label: 'Block Hours', align: 'right', render: r => r.block_hours != null ? <span className="text-purple">{Number(r.block_hours).toFixed(1)}</span> : '—' },
              { key: 'observations', label: 'Observations', align: 'right' },
              { key: 'first_seen', label: 'First Seen', render: r => r.first_seen ? new Date(r.first_seen as string).toLocaleTimeString() : '—' },
              { key: 'last_seen', label: 'Last Seen', render: r => r.last_seen ? new Date(r.last_seen as string).toLocaleTimeString() : '—' },
              { key: 'avg_fuel', label: 'Avg Fuel (kg/s)', align: 'right', render: r => r.avg_fuel != null ? <span className="text-warning">{Number(r.avg_fuel).toFixed(3)}</span> : '—' },
            ]}
            data={(fleet.data ?? []) as (FleetAircraft & Record<string, unknown>)[]}
            emptyMessage="No SWISS fleet data available yet. KPIs will populate as ADS-B data accumulates."
            maxRows={20}
          />
        </CardContent>
      </Card>

      {/* Route Frequency */}
      {routeFreq.data && routeFreq.data.length > 0 && (
        <Card className="mb-6">
          <CardHeader><CardTitle>Top Routes by Flight Count</CardTitle></CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={Math.min(400, routeFreq.data.length * 28 + 40)}>
              <BarChart data={routeFreq.data.slice(0, 15)} layout="vertical" margin={{ left: 80 }}>
                <CartesianGrid strokeDasharray="3 3" stroke={chartGridStroke} />
                <XAxis type="number" tick={chartAxisTick} />
                <YAxis
                  type="category"
                  dataKey={(d: Record<string, unknown>) => `${d.origin_icao}→${d.destination_icao}`}
                  tick={{ fontSize: 11, fill: 'var(--muted-foreground)' }}
                  width={80}
                />
                <Tooltip contentStyle={chartTooltipStyle} />
                <Bar dataKey="flight_count" fill={chartColors.sky} radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      )}

      {/* Route Performance */}
      <Card className="mb-6">
        <CardHeader><CardTitle>Route Performance</CardTitle></CardHeader>
        <CardContent>
          <div className="mb-3 flex gap-1.5">
            {([['', 'All'], ['overperforming', 'Overperforming'], ['average', 'Average'], ['underperforming', 'Underperforming']] as [PerfCategory, string][]).map(([cat, label]) => (
              <Button
                key={cat}
                variant={perfCategory === cat ? 'default' : 'outline'}
                size="sm"
                onClick={() => setPerfCategory(cat)}
              >
                {label}
              </Button>
            ))}
            <Button
              variant="outline"
              size="sm"
              className="ml-auto"
              onClick={async () => { await api.triggerRoutePerformanceCompute(); routePerf.refresh() }}
            >
              Recompute
            </Button>
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
                  return <span className={v > 0 ? 'text-danger' : v < 0 ? 'text-success' : ''}>{v > 0 ? '+' : ''}{v.toFixed(1)}%</span>
                },
              },
              {
                key: 'fuel_deviation_pct', label: 'Fuel Δ%', align: 'right',
                render: r => {
                  const v = r.fuel_deviation_pct
                  if (v == null) return '—'
                  return <span className={v > 0 ? 'text-danger' : v < 0 ? 'text-success' : ''}>{v > 0 ? '+' : ''}{v.toFixed(1)}%</span>
                },
              },
              { key: 'performance_score', label: 'Score', align: 'right', render: r => r.performance_score?.toFixed(1) ?? '—' },
              {
                key: 'category', label: 'Category',
                render: r => <StatusBadge label={r.category} color={PERF_COLORS[r.category] ?? '#94a3b8'} />,
              },
            ]}
            data={(routePerf.data ?? []) as (RoutePerformance & Record<string, unknown>)[]}
            emptyMessage="No route performance data. Run route performance computation first."
            maxRows={50}
          />
        </CardContent>
      </Card>
    </div>
  )
}
