'use client'

import { useState, useMemo } from 'react'
import {
  PieChart, Pie, Cell, Tooltip, ResponsiveContainer,
  LineChart, Line, XAxis, YAxis, CartesianGrid, Legend, BarChart, Bar,
} from 'recharts'
import { api } from '@/lib/api'
import { useApiData } from '@/hooks/useApiData'
import { Card, LoadingSpinner, ErrorBanner, EmptyState } from '@/components/ui'
import { colors, buttonPrimaryStyle, tooltipStyle } from '@/styles/theme'

const CASK_COLORS: Record<string, string> = {
  fuel: '#f59e0b',
  carbon: '#22c55e',
  navigation: '#3b82f6',
  airport: '#8b5cf6',
  crew: '#ec4899',
  other: '#6b7280',
}

const FACTOR_CARDS = [
  { key: 'jet_fuel_usd_gal', label: 'Jet Fuel', color: '#f59e0b' },
  { key: 'brent_crude_usd_bbl', label: 'Brent Crude', color: '#fb923c' },
  { key: 'eua_eur_ton', label: 'EU ETS Carbon', color: '#22c55e' },
  { key: 'eur_chf', label: 'EUR/CHF', color: '#3b82f6' },
  { key: 'usd_chf', label: 'USD/CHF', color: '#8b5cf6' },
]

export default function EconomicsPage() {
  const [refreshing, setRefreshing] = useState(false)
  const [selectedFactor, setSelectedFactor] = useState<string | null>(null)

  const factors = useApiData(() => api.getLatestEconomicFactors(), { refreshInterval: 300000 })
  const cask = useApiData(() => api.getCASKBreakdown(), { refreshInterval: 300000 })
  const ueHistoryRaw = useApiData(() => api.getUnitEconomicsHistory(24), { refreshInterval: 300000 })
  const factorHistory = useApiData(
    () => selectedFactor ? api.getFactorHistory(selectedFactor, 90) : Promise.resolve({ data: [], error: null, meta: {} }),
  )

  const ueHistory = useMemo(() => [...(ueHistoryRaw.data ?? [])].reverse(), [ueHistoryRaw.data])

  const pieData = useMemo(() => {
    if (!cask.data) return []
    return Object.entries(cask.data.components).map(([name, value]) => ({
      name: name.charAt(0).toUpperCase() + name.slice(1),
      value: Number(value.toFixed(2)),
      color: CASK_COLORS[name] || '#6b7280',
    }))
  }, [cask.data])

  const handleRefresh = async () => {
    setRefreshing(true)
    try {
      await api.refreshEconomicData()
      factors.refresh()
      cask.refresh()
      ueHistoryRaw.refresh()
    } catch { /* ignore */ }
    setRefreshing(false)
  }

  const handleFactorClick = (key: string) => {
    setSelectedFactor(prev => prev === key ? null : key)
  }

  const anyError = factors.error || cask.error || ueHistoryRaw.error
  if (factors.loading && cask.loading && ueHistoryRaw.loading) return <LoadingSpinner message="Loading financial data…" />

  return (
    <div style={{ padding: 24, overflowY: 'auto', height: '100%' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
        <h1 style={{ margin: 0, fontSize: 22, color: colors.text }}>Financial Intelligence</h1>
        <button onClick={handleRefresh} disabled={refreshing} style={{ ...buttonPrimaryStyle, opacity: refreshing ? 0.6 : 1 }}>
          {refreshing ? 'Refreshing…' : 'Refresh Data'}
        </button>
      </div>

      {anyError && <ErrorBanner message={anyError} onRetry={() => { factors.refresh(); cask.refresh(); ueHistoryRaw.refresh() }} />}

      {/* Economic Indicators */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(180px, 1fr))', gap: 12, marginBottom: 24 }}>
        {FACTOR_CARDS.map(fc => {
          const data = factors.data?.[fc.key]
          const isSelected = selectedFactor === fc.key
          return (
            <div
              key={fc.key}
              onClick={() => handleFactorClick(fc.key)}
              style={{
                background: isSelected ? colors.cardHover : colors.card,
                borderRadius: 8,
                padding: 16,
                cursor: 'pointer',
                border: isSelected ? `1px solid ${colors.accent}` : `1px solid transparent`,
                transition: 'all 0.15s',
              }}
            >
              <div style={{ fontSize: 11, color: colors.textMuted, textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 4 }}>
                {fc.label}
              </div>
              <div style={{ fontSize: 22, fontWeight: 700, color: fc.color }}>
                {data ? data.value.toFixed(fc.key.includes('chf') ? 4 : 2) : '—'}
              </div>
              <div style={{ fontSize: 11, color: colors.textDim }}>
                {data ? `${data.unit} (${data.source})` : 'Not yet fetched'}
              </div>
              {data && <div style={{ fontSize: 10, color: '#475569', marginTop: 2 }}>as of {data.date}</div>}
            </div>
          )
        })}
      </div>

      {/* Factor History Chart (shown when a factor card is clicked) */}
      {selectedFactor && (
        <Card
          title={`${FACTOR_CARDS.find(f => f.key === selectedFactor)?.label ?? selectedFactor} — 90 Day History`}
          style={{ marginBottom: 24 }}
        >
          {factorHistory.loading ? (
            <LoadingSpinner message="Loading history…" />
          ) : factorHistory.data && (factorHistory.data as unknown[]).length > 0 ? (
            <ResponsiveContainer width="100%" height={220}>
              <LineChart data={factorHistory.data as unknown[]}>
                <CartesianGrid strokeDasharray="3 3" stroke={colors.border} />
                <XAxis dataKey="date" tick={{ fontSize: 10, fill: colors.textMuted }}
                  tickFormatter={v => new Date(v).toLocaleDateString('en', { month: 'short', day: 'numeric' })} />
                <YAxis tick={{ fontSize: 10, fill: colors.textMuted }} />
                <Tooltip contentStyle={tooltipStyle} />
                <Line type="monotone" dataKey="value" stroke={FACTOR_CARDS.find(f => f.key === selectedFactor)?.color ?? colors.accent} strokeWidth={2} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          ) : (
            <EmptyState message="No historical data available for this factor" />
          )}
        </Card>
      )}

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(400px, 1fr))', gap: 16, marginBottom: 24 }}>
        {/* CASK Breakdown Pie */}
        <Card title="CASK Breakdown (CHF-cents per ASK)">
          {cask.data ? (
            <div style={{ display: 'flex', alignItems: 'center' }}>
              <ResponsiveContainer width="60%" height={240}>
                <PieChart>
                  <Pie data={pieData} dataKey="value" nameKey="name" cx="50%" cy="50%"
                    innerRadius={50} outerRadius={90} paddingAngle={2}>
                    {pieData.map((entry, i) => <Cell key={i} fill={entry.color} />)}
                  </Pie>
                  <Tooltip contentStyle={tooltipStyle} />
                </PieChart>
              </ResponsiveContainer>
              <div style={{ flex: 1, fontSize: 12 }}>
                {pieData.map(d => (
                  <div key={d.name} style={{ display: 'flex', justifyContent: 'space-between', padding: '3px 0', color: colors.text }}>
                    <span style={{ color: d.color }}>{d.name}</span>
                    <span>{d.value} ct</span>
                  </div>
                ))}
                <div style={{ borderTop: `1px solid ${colors.border}`, marginTop: 6, paddingTop: 6, fontWeight: 600, color: colors.text }}>
                  Total CASK: {cask.data.total_cask.toFixed(2)} ct
                </div>
              </div>
            </div>
          ) : (
            <EmptyState message="No CASK data yet. Run KPI computation first." />
          )}
        </Card>

        {/* CASK vs RASK Trend */}
        <Card title="CASK vs RASK Trend">
          <ResponsiveContainer width="100%" height={240}>
            <LineChart data={ueHistory}>
              <CartesianGrid strokeDasharray="3 3" stroke={colors.border} />
              <XAxis dataKey="period_start" tick={{ fontSize: 10, fill: colors.textMuted }}
                tickFormatter={v => new Date(v).toLocaleDateString('en', { month: 'short', day: 'numeric' })} />
              <YAxis tick={{ fontSize: 10, fill: colors.textMuted }} label={{ value: 'ct/ASK', angle: -90, position: 'insideLeft', fill: colors.textDim, fontSize: 10 }} />
              <Tooltip contentStyle={tooltipStyle} />
              <Legend wrapperStyle={{ fontSize: 11 }} />
              <Line type="monotone" dataKey="total_cask" stroke={colors.red} strokeWidth={2} dot={false} name="CASK" />
              <Line type="monotone" dataKey="estimated_rask" stroke={colors.green} strokeWidth={2} dot={false} name="RASK" />
            </LineChart>
          </ResponsiveContainer>
        </Card>
      </div>

      {/* CASK Component Stacked Trend */}
      <Card title="CASK Components Over Time">
        <ResponsiveContainer width="100%" height={280}>
          <BarChart data={ueHistory}>
            <CartesianGrid strokeDasharray="3 3" stroke={colors.border} />
            <XAxis dataKey="period_start" tick={{ fontSize: 10, fill: colors.textMuted }}
              tickFormatter={v => new Date(v).toLocaleDateString('en', { month: 'short', day: 'numeric' })} />
            <YAxis tick={{ fontSize: 10, fill: colors.textMuted }} />
            <Tooltip contentStyle={tooltipStyle} />
            <Legend wrapperStyle={{ fontSize: 11 }} />
            <Bar dataKey="fuel_cost_per_ask" stackId="cask" fill="#f59e0b" name="Fuel" />
            <Bar dataKey="carbon_cost_per_ask" stackId="cask" fill="#22c55e" name="Carbon" />
            <Bar dataKey="nav_charges_per_ask" stackId="cask" fill="#3b82f6" name="Navigation" />
            <Bar dataKey="airport_cost_per_ask" stackId="cask" fill="#8b5cf6" name="Airport" />
            <Bar dataKey="crew_cost_per_ask" stackId="cask" fill="#ec4899" name="Crew" />
            <Bar dataKey="other_cost_per_ask" stackId="cask" fill="#6b7280" name="Other" />
          </BarChart>
        </ResponsiveContainer>
      </Card>
    </div>
  )
}
