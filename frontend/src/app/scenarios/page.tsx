'use client'

import { useState } from 'react'
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts'
import { api } from '@/lib/api'
import { useApiData } from '@/hooks/useApiData'
import { Card, CardHeader, CardTitle, CardContent, DataTable, LoadingSpinner, ErrorBanner, StatusBadge, Button, Input, Label } from '@/components/ui'
import { chartTooltipStyle, chartAxisTick, chartColors } from '@/lib/chart-theme'
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
    <div className="h-full overflow-y-auto p-6">
      <h1 className="mb-5 text-xl font-bold text-foreground">Scenario Engine</h1>

      {anyError && <ErrorBanner message={anyError} onRetry={() => { presets.refresh(); history.refresh() }} />}

      <div className="mb-6 grid grid-cols-[repeat(auto-fill,minmax(400px,1fr))] gap-4">
        {/* Preset Scenarios */}
        <Card>
          <CardHeader><CardTitle>Scenario Presets</CardTitle></CardHeader>
          <CardContent>
            <div className="flex flex-col gap-2">
              {(presets.data ?? []).map(p => (
                <button
                  key={p.name}
                  onClick={() => runScenario(p.name, p.description, p.parameters)}
                  disabled={running}
                  className="flex items-center justify-between rounded-lg border border-border bg-background p-3 text-left text-sm text-foreground transition-colors hover:bg-secondary disabled:cursor-wait"
                >
                  <div>
                    <div className="mb-0.5 font-semibold">{p.name}</div>
                    <div className="text-[11px] text-muted-foreground">{p.description}</div>
                  </div>
                  <span className="ml-3 text-lg text-primary">&rarr;</span>
                </button>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Custom Scenario Builder */}
        <Card>
          <CardHeader><CardTitle>Custom Scenario</CardTitle></CardHeader>
          <CardContent>
            <div className="flex flex-col gap-3">
              {[
                { key: 'fuel_price_change_pct', label: 'Fuel Price Change (%)' },
                { key: 'carbon_price_change_pct', label: 'Carbon Price Change (%)' },
                { key: 'load_factor_change_pct', label: 'Load Factor Change (%)' },
                { key: 'capacity_change_pct', label: 'Capacity Change (%)' },
              ].map(field => (
                <div key={field.key} className="flex items-center gap-2.5">
                  <Label className="w-44 text-sm text-muted-foreground">{field.label}</Label>
                  <Input
                    type="number"
                    value={customParams[field.key]}
                    onChange={e => setCustomParams(prev => ({ ...prev, [field.key]: e.target.value }))}
                    className="flex-1"
                  />
                </div>
              ))}
              <Button
                onClick={runCustom}
                disabled={running}
                className="mt-2 bg-success text-background hover:bg-success/80"
              >
                {running ? 'Running…' : 'Run Scenario'}
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Results */}
      {activeResult && (
        <div className="mb-6 grid grid-cols-[repeat(auto-fill,minmax(400px,1fr))] gap-4">
          <Card>
            <CardHeader><CardTitle>Scenario Result: {activeName}</CardTitle></CardHeader>
            <CardContent>
              <div className="mb-3 text-sm text-muted-foreground">
                {activeResult.impact_summary}
              </div>
              <div className="grid grid-cols-3 gap-3">
                {[
                  { label: 'Baseline CASK', value: activeResult.baseline.total_cask, unit: 'ct/ASK' },
                  { label: 'Scenario CASK', value: activeResult.scenario.total_cask, unit: 'ct/ASK' },
                  { label: 'CASK Delta', value: activeResult.deltas.total_cask, unit: 'ct/ASK',
                    color: activeResult.deltas.total_cask > 0 ? chartColors.red : chartColors.green },
                  { label: 'Baseline RASK', value: activeResult.baseline.estimated_rask, unit: 'ct/ASK' },
                  { label: 'Scenario RASK', value: activeResult.scenario.estimated_rask, unit: 'ct/ASK' },
                  { label: 'Spread Delta', value: activeResult.deltas.spread, unit: 'ct/ASK',
                    color: activeResult.deltas.spread > 0 ? chartColors.green : chartColors.red },
                ].map(item => (
                  <div key={item.label} className="rounded-md bg-background p-2">
                    <div className="mb-0.5 text-[10px] text-muted-foreground">{item.label}</div>
                    <div className="text-lg font-bold" style={{ color: item.color }}>
                      {item.value >= 0 && item.color ? '+' : ''}{item.value.toFixed(2)}
                    </div>
                    <div className="text-[10px] text-muted-foreground/60">{item.unit}</div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader><CardTitle>Impact by Component</CardTitle></CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={240}>
                <BarChart data={deltaBar} layout="vertical" margin={{ left: 80 }}>
                  <XAxis type="number" tick={chartAxisTick} />
                  <YAxis type="category" dataKey="name" tick={{ fontSize: 12, fill: 'var(--muted-foreground)' }} width={80} />
                  <Tooltip contentStyle={chartTooltipStyle}
                    formatter={(v: number) => `${v >= 0 ? '+' : ''}${v.toFixed(4)} ct/ASK`} />
                  <Bar dataKey="delta" radius={[0, 4, 4, 0]}>
                    {deltaBar.map((entry, i) => (
                      <Cell key={i} fill={entry.delta >= 0 ? chartColors.red : chartColors.green} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Scenario History */}
      <Card>
        <CardHeader><CardTitle>Scenario History</CardTitle></CardHeader>
        <CardContent>
          <DataTable<Scenario & Record<string, unknown>>
            columns={[
              { key: 'name', label: 'Name' },
              {
                key: 'status', label: 'Status',
                render: r => <StatusBadge label={r.status} color={r.status === 'completed' ? chartColors.green : chartColors.orange} />,
              },
              {
                key: 'parameters', label: 'Parameters',
                render: r => <span className="font-mono text-[11px] text-muted-foreground">{JSON.stringify(r.parameters)}</span>,
              },
              {
                key: 'created_at', label: 'Created',
                render: r => <span className="text-[11px]">{new Date(r.created_at).toLocaleString()}</span>,
              },
            ]}
            data={(history.data ?? []) as (Scenario & Record<string, unknown>)[]}
            emptyMessage="No scenarios run yet."
          />
        </CardContent>
      </Card>
    </div>
  )
}
