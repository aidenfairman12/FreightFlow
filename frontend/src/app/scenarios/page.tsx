'use client'

import { useState } from 'react'
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts'
import { api } from '@/lib/api'
import { useApiData } from '@/hooks/useApiData'
import { Card, DataTable, LoadingSpinner, ErrorBanner, StatusBadge } from '@/components/ui'
import { colors, buttonStyle, tooltipStyle } from '@/styles/theme'
import type { ScenarioResults, Scenario } from '@/types'

export default function ScenariosPage() {
  const [activeResult, setActiveResult] = useState<ScenarioResults | null>(null)
  const [activeName, setActiveName] = useState('')
  const [running, setRunning] = useState(false)
  const [customParams, setCustomParams] = useState<Record<string, string>>({
    fuel_price_change_pct: '0',
    carbon_price_change_pct: '0',
    load_factor_change_pct: '0',
    capacity_change_pct: '0',
  })

  const presets = useApiData(() => api.getScenarioPresets())
  const history = useApiData(() => api.listScenarios(10))

  const runScenario = async (name: string, description: string, parameters: Record<string, number>) => {
    setRunning(true)
    setActiveName(name)
    setActiveResult(null)
    try {
      const res = await api.createScenario({ name, description, parameters })
      if (res.data) setActiveResult(res.data as ScenarioResults)
      history.refresh()
    } catch { /* ignore */ }
    setRunning(false)
  }

  const runCustom = () => {
    const params: Record<string, number> = {}
    for (const [k, v] of Object.entries(customParams)) {
      const num = parseFloat(v)
      if (num !== 0) params[k] = num
    }
    if (Object.keys(params).length === 0) return
    runScenario('Custom Scenario', 'User-defined scenario', params)
  }

  const deltaBar = activeResult ? [
    { name: 'CASK', delta: activeResult.deltas.total_cask },
    { name: 'RASK', delta: activeResult.deltas.estimated_rask },
    { name: 'Spread', delta: activeResult.deltas.spread },
    { name: 'Fuel/ASK', delta: activeResult.deltas.fuel_cost_per_ask },
    { name: 'Carbon/ASK', delta: activeResult.deltas.carbon_cost_per_ask },
  ] : []

  const anyError = presets.error || history.error
  if (presets.loading && history.loading) return <LoadingSpinner message="Loading scenarios…" />

  return (
    <div style={{ padding: 24, overflowY: 'auto', height: '100%' }}>
      <h1 style={{ margin: '0 0 20px', fontSize: 22, color: colors.text }}>Scenario Engine</h1>

      {anyError && <ErrorBanner message={anyError} onRetry={() => { presets.refresh(); history.refresh() }} />}

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(400px, 1fr))', gap: 16, marginBottom: 24 }}>
        {/* Preset Scenarios */}
        <Card title="Scenario Presets">
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {(presets.data ?? []).map(p => (
              <button
                key={p.name}
                onClick={() => runScenario(p.name, p.description, p.parameters)}
                disabled={running}
                style={{
                  display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                  padding: '10px 14px', background: colors.bg, border: `1px solid ${colors.border}`,
                  borderRadius: 6, cursor: running ? 'wait' : 'pointer', color: colors.text,
                  textAlign: 'left', fontSize: 13,
                }}
              >
                <div>
                  <div style={{ fontWeight: 600, marginBottom: 2 }}>{p.name}</div>
                  <div style={{ fontSize: 11, color: colors.textDim }}>{p.description}</div>
                </div>
                <span style={{ color: colors.accent, fontSize: 18, marginLeft: 12 }}>&rarr;</span>
              </button>
            ))}
          </div>
        </Card>

        {/* Custom Scenario Builder */}
        <Card title="Custom Scenario">
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            {[
              { key: 'fuel_price_change_pct', label: 'Fuel Price Change (%)' },
              { key: 'carbon_price_change_pct', label: 'Carbon Price Change (%)' },
              { key: 'load_factor_change_pct', label: 'Load Factor Change (%)' },
              { key: 'capacity_change_pct', label: 'Capacity Change (%)' },
            ].map(field => (
              <div key={field.key} style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                <label style={{ fontSize: 13, color: colors.textMuted, width: 180 }}>{field.label}</label>
                <input
                  type="number"
                  value={customParams[field.key]}
                  onChange={e => setCustomParams(prev => ({ ...prev, [field.key]: e.target.value }))}
                  style={{
                    flex: 1, padding: '6px 10px', background: colors.bg, border: `1px solid ${colors.border}`,
                    borderRadius: 4, color: colors.text, fontSize: 13, outline: 'none',
                  }}
                />
              </div>
            ))}
            <button
              onClick={runCustom}
              disabled={running}
              style={{
                marginTop: 8, padding: '10px 16px', background: colors.green, color: colors.bg,
                border: 'none', borderRadius: 6, fontWeight: 600, cursor: running ? 'wait' : 'pointer', fontSize: 13,
              }}
            >
              {running ? 'Running…' : 'Run Scenario'}
            </button>
          </div>
        </Card>
      </div>

      {/* Results */}
      {activeResult && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(400px, 1fr))', gap: 16, marginBottom: 24 }}>
          <Card title={`Scenario Result: ${activeName}`}>
            <div style={{ fontSize: 13, color: colors.textMuted, marginBottom: 12 }}>
              {activeResult.impact_summary}
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 12 }}>
              {[
                { label: 'Baseline CASK', value: activeResult.baseline.total_cask, unit: 'ct/ASK' },
                { label: 'Scenario CASK', value: activeResult.scenario.total_cask, unit: 'ct/ASK' },
                { label: 'CASK Delta', value: activeResult.deltas.total_cask, unit: 'ct/ASK',
                  color: activeResult.deltas.total_cask > 0 ? colors.red : colors.green },
                { label: 'Baseline RASK', value: activeResult.baseline.estimated_rask, unit: 'ct/ASK' },
                { label: 'Scenario RASK', value: activeResult.scenario.estimated_rask, unit: 'ct/ASK' },
                { label: 'Spread Delta', value: activeResult.deltas.spread, unit: 'ct/ASK',
                  color: activeResult.deltas.spread > 0 ? colors.green : colors.red },
              ].map(item => (
                <div key={item.label} style={{ padding: 8, background: colors.bg, borderRadius: 6 }}>
                  <div style={{ fontSize: 10, color: colors.textDim, marginBottom: 2 }}>{item.label}</div>
                  <div style={{ fontSize: 18, fontWeight: 700, color: item.color ?? colors.text }}>
                    {item.value >= 0 && item.color ? '+' : ''}{item.value.toFixed(2)}
                  </div>
                  <div style={{ fontSize: 10, color: '#475569' }}>{item.unit}</div>
                </div>
              ))}
            </div>
          </Card>

          <Card title="Impact by Component">
            <ResponsiveContainer width="100%" height={240}>
              <BarChart data={deltaBar} layout="vertical" margin={{ left: 80 }}>
                <XAxis type="number" tick={{ fontSize: 10, fill: colors.textMuted }} />
                <YAxis type="category" dataKey="name" tick={{ fontSize: 12, fill: colors.textMuted }} width={80} />
                <Tooltip contentStyle={tooltipStyle}
                  formatter={(v: number) => `${v >= 0 ? '+' : ''}${v.toFixed(4)} ct/ASK`} />
                <Bar dataKey="delta" radius={[0, 4, 4, 0]}>
                  {deltaBar.map((entry, i) => (
                    <Cell key={i} fill={entry.delta >= 0 ? colors.red : colors.green} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </Card>
        </div>
      )}

      {/* Scenario History */}
      <Card title="Scenario History">
        <DataTable<Scenario & Record<string, unknown>>
          columns={[
            { key: 'name', label: 'Name' },
            {
              key: 'status', label: 'Status',
              render: r => <StatusBadge label={r.status} color={r.status === 'completed' ? colors.green : colors.orange} />,
            },
            {
              key: 'parameters', label: 'Parameters',
              render: r => <span style={{ fontSize: 11, fontFamily: 'monospace', color: colors.textMuted }}>{JSON.stringify(r.parameters)}</span>,
            },
            {
              key: 'created_at', label: 'Created',
              render: r => <span style={{ fontSize: 11 }}>{new Date(r.created_at).toLocaleString()}</span>,
            },
          ]}
          data={(history.data ?? []) as (Scenario & Record<string, unknown>)[]}
          emptyMessage="No scenarios run yet."
        />
      </Card>
    </div>
  )
}
