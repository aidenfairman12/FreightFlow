'use client'

import { useState, useMemo } from 'react'
import {
  PieChart, Pie, Cell, Tooltip, ResponsiveContainer,
  LineChart, Line, XAxis, YAxis, CartesianGrid, Legend, BarChart, Bar,
} from 'recharts'
import { api } from '@/lib/api'
import { useApiData } from '@/hooks/useApiData'
import { Card, CardHeader, CardTitle, CardContent, LoadingSpinner, ErrorBanner, EmptyState, Button } from '@/components/ui'
import { cn } from '@/lib/utils'
import { chartTooltipStyle, chartAxisTick, chartGridStroke } from '@/lib/chart-theme'

const COST_COLORS: Record<string, string> = {
  fuel: '#f59e0b',
  labor: '#3b82f6',
  equipment: '#a78bfa',
  insurance: '#22c55e',
  tolls_fees: '#ec4899',
  other: '#6b7280',
}

const FACTOR_CARDS = [
  { key: 'diesel_usd_gal', label: 'Diesel', color: '#f59e0b' },
  { key: 'brent_crude_usd_bbl', label: 'Brent Crude', color: '#fb923c' },
  { key: 'freight_tsi', label: 'Freight TSI', color: '#3b82f6' },
  { key: 'trucking_ppi', label: 'Trucking PPI', color: '#a78bfa' },
]

export default function EconomicsPage() {
  const [refreshing, setRefreshing] = useState(false)
  const [selectedFactor, setSelectedFactor] = useState<string | null>(null)

  const factors = useApiData(() => api.getLatestEconomicFactors(), { refreshInterval: 300000 })
  const costBreakdown = useApiData(() => api.getCostBreakdown(), { refreshInterval: 300000 })
  const ueHistoryRaw = useApiData(() => api.getUnitEconomicsHistory(20), { refreshInterval: 300000 })
  const factorHistory = useApiData(
    () => selectedFactor ? api.getFactorHistory(selectedFactor, 90) : Promise.resolve({ data: [], error: null, meta: {} }),
  )

  const ueHistory = useMemo(() => [...(ueHistoryRaw.data ?? [])].reverse(), [ueHistoryRaw.data])

  const pieData = useMemo(() => {
    if (!costBreakdown.data) return []
    return Object.entries(costBreakdown.data.components).map(([name, value]) => ({
      name: name.charAt(0).toUpperCase() + name.slice(1).replace('_', ' '),
      value: Number(value.toFixed(4)),
      color: COST_COLORS[name] || '#6b7280',
    }))
  }, [costBreakdown.data])

  const handleRefresh = async () => {
    setRefreshing(true)
    try {
      await api.refreshEconomicData()
      factors.refresh()
      costBreakdown.refresh()
      ueHistoryRaw.refresh()
    } catch { /* ignore */ }
    setRefreshing(false)
  }

  const handleFactorClick = (key: string) => {
    setSelectedFactor(prev => prev === key ? null : key)
  }

  const anyError = factors.error || costBreakdown.error || ueHistoryRaw.error
  if (factors.loading && costBreakdown.loading && ueHistoryRaw.loading) return <LoadingSpinner message="Loading economic data…" />

  return (
    <div className="h-full overflow-y-auto p-6">
      <div className="mb-5 flex items-center justify-between">
        <h1 className="text-xl font-bold text-foreground">Freight Cost Intelligence</h1>
        <Button onClick={handleRefresh} disabled={refreshing}>
          {refreshing ? 'Refreshing…' : 'Refresh Data'}
        </Button>
      </div>

      {anyError && <ErrorBanner message={anyError} onRetry={() => { factors.refresh(); costBreakdown.refresh(); ueHistoryRaw.refresh() }} />}

      {/* Economic Indicators */}
      <div className="mb-6 grid grid-cols-[repeat(auto-fill,minmax(180px,1fr))] gap-3">
        {FACTOR_CARDS.map(fc => {
          const data = factors.data?.[fc.key]
          const isSelected = selectedFactor === fc.key
          return (
            <div
              key={fc.key}
              onClick={() => handleFactorClick(fc.key)}
              className={cn(
                'cursor-pointer rounded-xl p-4 transition-all ring-1',
                isSelected
                  ? 'bg-secondary ring-primary'
                  : 'bg-card ring-foreground/10 hover:bg-secondary/50',
              )}
            >
              <div className="mb-1 text-[11px] font-medium uppercase tracking-wider text-muted-foreground">
                {fc.label}
              </div>
              <div className="text-[22px] font-bold" style={{ color: fc.color }}>
                {data ? data.value.toFixed(2) : '—'}
              </div>
              <div className="text-[11px] text-muted-foreground">
                {data ? `${data.unit} (${data.source})` : 'Not yet fetched'}
              </div>
              {data && <div className="mt-0.5 text-[10px] text-muted-foreground/60">as of {data.date}</div>}
            </div>
          )
        })}
      </div>

      {/* Factor History Chart */}
      {selectedFactor && (
        <Card className="mb-6">
          <CardHeader>
            <CardTitle>{FACTOR_CARDS.find(f => f.key === selectedFactor)?.label ?? selectedFactor} — 90 Day History</CardTitle>
          </CardHeader>
          <CardContent>
            {factorHistory.loading ? (
              <LoadingSpinner message="Loading history…" />
            ) : factorHistory.data && (factorHistory.data as unknown[]).length > 0 ? (
              <ResponsiveContainer width="100%" height={220}>
                <LineChart data={factorHistory.data as unknown[]}>
                  <CartesianGrid strokeDasharray="3 3" stroke={chartGridStroke} />
                  <XAxis dataKey="date" tick={chartAxisTick}
                    tickFormatter={v => new Date(v).toLocaleDateString('en', { month: 'short', day: 'numeric' })} />
                  <YAxis tick={chartAxisTick} />
                  <Tooltip contentStyle={chartTooltipStyle} />
                  <Line type="monotone" dataKey="value" stroke={FACTOR_CARDS.find(f => f.key === selectedFactor)?.color ?? '#38bdf8'} strokeWidth={2} dot={false} />
                </LineChart>
              </ResponsiveContainer>
            ) : (
              <EmptyState message="No historical data available for this factor" />
            )}
          </CardContent>
        </Card>
      )}

      <div className="mb-6 grid grid-cols-[repeat(auto-fill,minmax(400px,1fr))] gap-4">
        {/* Cost Breakdown Pie */}
        <Card>
          <CardHeader><CardTitle>Cost per Ton-Mile Breakdown</CardTitle></CardHeader>
          <CardContent>
            {costBreakdown.data ? (
              <div className="flex items-center">
                <ResponsiveContainer width="60%" height={240}>
                  <PieChart>
                    <Pie data={pieData} dataKey="value" nameKey="name" cx="50%" cy="50%"
                      innerRadius={50} outerRadius={90} paddingAngle={2}>
                      {pieData.map((entry, i) => <Cell key={i} fill={entry.color} />)}
                    </Pie>
                    <Tooltip contentStyle={chartTooltipStyle} />
                  </PieChart>
                </ResponsiveContainer>
                <div className="flex-1 text-xs">
                  {pieData.map(d => (
                    <div key={d.name} className="flex justify-between py-0.5 text-foreground">
                      <span style={{ color: d.color }}>{d.name}</span>
                      <span>${d.value.toFixed(4)}</span>
                    </div>
                  ))}
                  <div className="mt-1.5 border-t border-border pt-1.5 font-semibold text-foreground">
                    Total: ${costBreakdown.data.total_cost_per_tm.toFixed(4)}/tm
                  </div>
                </div>
              </div>
            ) : (
              <EmptyState message="No cost data yet. Run KPI computation first." />
            )}
          </CardContent>
        </Card>

        {/* Cost vs Revenue Trend */}
        <Card>
          <CardHeader><CardTitle>Cost vs Revenue per Ton-Mile</CardTitle></CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={240}>
              <LineChart data={ueHistory}>
                <CartesianGrid strokeDasharray="3 3" stroke={chartGridStroke} />
                <XAxis dataKey="year" tick={chartAxisTick} />
                <YAxis tick={chartAxisTick} label={{ value: '$/tm', angle: -90, position: 'insideLeft', fill: 'var(--muted-foreground)', fontSize: 10 }} />
                <Tooltip contentStyle={chartTooltipStyle} formatter={(v: number) => `$${v.toFixed(4)}`} />
                <Legend wrapperStyle={{ fontSize: 11 }} />
                <Line type="monotone" dataKey="total_cost_per_tm" stroke="#ef4444" strokeWidth={2} dot={false} name="Cost/TM" />
                <Line type="monotone" dataKey="revenue_per_tm" stroke="#22c55e" strokeWidth={2} dot={false} name="Revenue/TM" />
              </LineChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </div>

      {/* Cost Component Stacked Trend */}
      <Card>
        <CardHeader><CardTitle>Cost Components Over Time</CardTitle></CardHeader>
        <CardContent>
          <ResponsiveContainer width="100%" height={280}>
            <BarChart data={ueHistory}>
              <CartesianGrid strokeDasharray="3 3" stroke={chartGridStroke} />
              <XAxis dataKey="year" tick={chartAxisTick} />
              <YAxis tick={chartAxisTick} tickFormatter={v => `$${v}`} />
              <Tooltip contentStyle={chartTooltipStyle} formatter={(v: number) => `$${v.toFixed(4)}`} />
              <Legend wrapperStyle={{ fontSize: 11 }} />
              <Bar dataKey="fuel_cost_per_tm" stackId="cost" fill="#f59e0b" name="Fuel" />
              <Bar dataKey="labor_cost_per_tm" stackId="cost" fill="#3b82f6" name="Labor" />
              <Bar dataKey="equipment_cost_per_tm" stackId="cost" fill="#a78bfa" name="Equipment" />
              <Bar dataKey="insurance_cost_per_tm" stackId="cost" fill="#22c55e" name="Insurance" />
              <Bar dataKey="tolls_fees_per_tm" stackId="cost" fill="#ec4899" name="Tolls/Fees" />
              <Bar dataKey="other_cost_per_tm" stackId="cost" fill="#6b7280" name="Other" />
            </BarChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>
    </div>
  )
}
