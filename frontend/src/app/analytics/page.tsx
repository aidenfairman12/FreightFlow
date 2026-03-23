'use client'

import { useState, useMemo } from 'react'
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  LineChart, Line, CartesianGrid, AreaChart, Area, Legend,
} from 'recharts'
import { api } from '@/lib/api'
import { useApiData } from '@/hooks/useApiData'
import { Card, CardHeader, CardTitle, CardContent, DataTable, LoadingSpinner, ErrorBanner, Button } from '@/components/ui'
import { chartTooltipStyle, chartAxisTick, chartGridStroke, chartColors } from '@/lib/chart-theme'

function KPICard({ label, value, unit, color }: { label: string; value: string; unit: string; color: string }) {
  return (
    <Card>
      <CardContent className="pt-4">
        <div className="mb-1 text-[11px] font-medium uppercase tracking-wider text-muted-foreground">{label}</div>
        <div className="text-2xl font-bold" style={{ color }}>{value}</div>
        <div className="text-[11px] text-muted-foreground">{unit}</div>
      </CardContent>
    </Card>
  )
}

function fmtNum(n: number | null | undefined, decimals = 1): string {
  if (n == null) return '—'
  if (Math.abs(n) >= 1e6) return `${(n / 1e6).toFixed(decimals)}M`
  if (Math.abs(n) >= 1e3) return `${(n / 1e3).toFixed(decimals)}K`
  return n.toFixed(decimals)
}

export default function AnalyticsPage() {
  const [computing, setComputing] = useState(false)

  const kpi = useApiData(() => api.getCurrentKPIs(), { refreshInterval: 60000 })
  const kpiHistory = useApiData(() => api.getKPIHistory('national', 20), { refreshInterval: 60000 })
  const modeShare = useApiData(() => api.getModeShare(), { refreshInterval: 120000 })
  const modeComparison = useApiData(() => api.getModeComparison(2022), { refreshInterval: 120000 })
  const topCommodities = useApiData(() => api.getCommoditySummary(2022, 15), { refreshInterval: 300000 })
  const corridorPerf = useApiData(() => api.getCorridorPerformance(), { refreshInterval: 120000 })

  const historyData = useMemo(() => [...(kpiHistory.data ?? [])].reverse(), [kpiHistory.data])
  const k = kpi.data

  const handleCompute = async () => {
    setComputing(true)
    try {
      await api.triggerKPICompute(2022)
      kpi.refresh()
      kpiHistory.refresh()
    } catch { /* ignore */ }
    setComputing(false)
  }

  const anyError = kpi.error || kpiHistory.error || modeComparison.error
  if (kpi.loading && kpiHistory.loading) return <LoadingSpinner message="Loading freight KPIs…" />

  return (
    <div className="h-full overflow-y-auto p-6">
      <div className="mb-5 flex items-center justify-between">
        <h1 className="text-xl font-bold text-foreground">Freight Analytics</h1>
        <Button onClick={handleCompute} disabled={computing}>
          {computing ? 'Computing…' : 'Refresh KPIs'}
        </Button>
      </div>

      {anyError && <ErrorBanner message={anyError} onRetry={() => { kpi.refresh(); kpiHistory.refresh() }} />}

      {/* KPI Cards */}
      <div className="mb-6 grid grid-cols-[repeat(auto-fill,minmax(180px,1fr))] gap-3">
        <KPICard label="Total Tons" value={fmtNum(k?.total_tons)} unit="thousands" color={chartColors.sky} />
        <KPICard label="Total Value" value={k?.total_value_usd != null ? `$${fmtNum(k.total_value_usd)}` : '—'} unit="USD" color={chartColors.green} />
        <KPICard label="Ton-Miles" value={fmtNum(k?.total_ton_miles)} unit="millions" color={chartColors.purple} />
        <KPICard label="Truck Share" value={k?.truck_share_pct != null ? `${k.truck_share_pct.toFixed(1)}%` : '—'} unit="by tonnage" color={chartColors.red} />
        <KPICard label="Rail Share" value={k?.rail_share_pct != null ? `${k.rail_share_pct.toFixed(1)}%` : '—'} unit="by tonnage" color={chartColors.sky} />
        <KPICard label="Avg Cost/TM" value={k?.avg_cost_per_ton_mile != null ? `$${k.avg_cost_per_ton_mile.toFixed(3)}` : '—'} unit="per ton-mile" color={chartColors.orange} />
        <KPICard label="Value/Ton" value={k?.value_per_ton != null ? `$${k.value_per_ton.toFixed(0)}` : '—'} unit="USD per ton" color={chartColors.cyan} />
        <KPICard label="Avg Haul" value={k?.ton_miles_per_ton != null ? `${k.ton_miles_per_ton.toFixed(0)}` : '—'} unit="miles per ton" color="#fb923c" />
      </div>

      {/* Charts Row */}
      <div className="mb-6 grid grid-cols-[repeat(auto-fill,minmax(400px,1fr))] gap-4">
        {/* Volume Trend */}
        <Card>
          <CardHeader><CardTitle>Freight Volume Trend</CardTitle></CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={220}>
              <LineChart data={historyData}>
                <CartesianGrid strokeDasharray="3 3" stroke={chartGridStroke} />
                <XAxis dataKey="period_year" tick={chartAxisTick} />
                <YAxis tick={chartAxisTick} tickFormatter={v => fmtNum(v)} />
                <Tooltip contentStyle={chartTooltipStyle} formatter={(v: number) => fmtNum(v)} />
                <Line type="monotone" dataKey="total_tons" stroke={chartColors.sky} strokeWidth={2} dot={false} name="Tons (K)" />
                <Line type="monotone" dataKey="total_ton_miles" stroke={chartColors.purple} strokeWidth={2} dot={false} name="Ton-Miles (M)" />
              </LineChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        {/* Mode Share Stacked Area */}
        <Card>
          <CardHeader><CardTitle>Mode Share Over Time</CardTitle></CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={220}>
              <AreaChart data={modeShare.data ?? []}>
                <CartesianGrid strokeDasharray="3 3" stroke={chartGridStroke} />
                <XAxis dataKey="period_year" tick={chartAxisTick} />
                <YAxis tick={chartAxisTick} tickFormatter={v => `${v}%`} />
                <Tooltip contentStyle={chartTooltipStyle} formatter={(v: number) => `${v.toFixed(1)}%`} />
                <Legend wrapperStyle={{ fontSize: 11 }} />
                <Area type="monotone" dataKey="truck_share_pct" stackId="1" fill={chartColors.red} stroke={chartColors.red} name="Truck" />
                <Area type="monotone" dataKey="rail_share_pct" stackId="1" fill={chartColors.sky} stroke={chartColors.sky} name="Rail" />
                <Area type="monotone" dataKey="water_share_pct" stackId="1" fill={chartColors.cyan} stroke={chartColors.cyan} name="Water" />
                <Area type="monotone" dataKey="air_share_pct" stackId="1" fill={chartColors.orange} stroke={chartColors.orange} name="Air" />
                <Area type="monotone" dataKey="multi_share_pct" stackId="1" fill={chartColors.purple} stroke={chartColors.purple} name="Multi" />
              </AreaChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </div>

      {/* Mode Cost Comparison */}
      {modeComparison.data && modeComparison.data.length > 0 && (
        <Card className="mb-6">
          <CardHeader><CardTitle>Cost per Ton-Mile by Mode (2022)</CardTitle></CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={Math.min(300, modeComparison.data.length * 45 + 40)}>
              <BarChart data={modeComparison.data} layout="vertical" margin={{ left: 90 }}>
                <CartesianGrid strokeDasharray="3 3" stroke={chartGridStroke} />
                <XAxis type="number" tick={chartAxisTick} tickFormatter={v => `$${v}`} />
                <YAxis type="category" dataKey="mode_name" tick={{ fontSize: 11, fill: 'var(--muted-foreground)' }} width={90} />
                <Tooltip contentStyle={chartTooltipStyle} formatter={(v: number) => `$${v.toFixed(3)}`} />
                <Bar dataKey="cost_per_ton_mile" fill={chartColors.sky} radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      )}

      {/* Top Commodities */}
      {topCommodities.data && topCommodities.data.length > 0 && (
        <Card className="mb-6">
          <CardHeader><CardTitle>Top Commodities by Volume (2022)</CardTitle></CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={Math.min(500, topCommodities.data.length * 28 + 40)}>
              <BarChart data={topCommodities.data.slice(0, 15)} layout="vertical" margin={{ left: 140 }}>
                <CartesianGrid strokeDasharray="3 3" stroke={chartGridStroke} />
                <XAxis type="number" tick={chartAxisTick} tickFormatter={v => fmtNum(v)} />
                <YAxis type="category" dataKey="commodity_name" tick={{ fontSize: 10, fill: 'var(--muted-foreground)' }} width={140} />
                <Tooltip contentStyle={chartTooltipStyle} formatter={(v: number) => `${fmtNum(v)} K tons`} />
                <Bar dataKey="total_tons_k" fill={chartColors.green} radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      )}

      {/* Corridor Performance Table */}
      <Card className="mb-6">
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle>Corridor Performance</CardTitle>
            <Button
              variant="outline"
              size="sm"
              onClick={async () => { await api.triggerCorridorPerformanceCompute(); corridorPerf.refresh() }}
            >
              Recompute
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          {corridorPerf.error && <ErrorBanner message={corridorPerf.error} onRetry={corridorPerf.refresh} />}
          <DataTable<Record<string, unknown>>
            columns={[
              { key: 'name', label: 'Corridor' },
              { key: 'total_tons', label: 'Tons (K)', align: 'right', render: r => fmtNum(r.total_tons as number) },
              { key: 'total_value_usd', label: 'Value', align: 'right', render: r => r.total_value_usd != null ? `$${fmtNum(r.total_value_usd as number)}` : '—' },
              { key: 'estimated_cost', label: 'Est. Cost', align: 'right', render: r => r.estimated_cost != null ? `$${fmtNum(r.estimated_cost as number)}` : '—' },
              { key: 'cost_per_ton', label: '$/Ton', align: 'right', render: r => r.cost_per_ton != null ? `$${(r.cost_per_ton as number).toFixed(2)}` : '—' },
            ]}
            data={corridorPerf.data ?? []}
            emptyMessage="No corridor performance data. Click Recompute to generate."
            maxRows={20}
          />
        </CardContent>
      </Card>
    </div>
  )
}
