'use client'

import dynamic from 'next/dynamic'
import { useState, useCallback } from 'react'
import { api } from '@/lib/api'
import { useApiData } from '@/hooks/useApiData'
import { Card, CardHeader, CardTitle, CardContent, ErrorBanner, LoadingSpinner } from '@/components/ui'
import { chartColors } from '@/lib/chart-theme'
import type { Corridor, CorridorCostData } from '@/types'

const FreightMap = dynamic(() => import('@/components/Map/FreightMap'), { ssr: false })

function fmt(n: number | null | undefined, decimals = 1): string {
  if (n == null) return '—'
  if (Math.abs(n) >= 1e6) return `${(n / 1e6).toFixed(decimals)}M`
  if (Math.abs(n) >= 1e3) return `${(n / 1e3).toFixed(decimals)}K`
  return n.toFixed(decimals)
}

export default function DashboardPage() {
  const [selected, setSelected] = useState<Corridor | null>(null)
  const [modeData, setModeData] = useState<CorridorCostData | null>(null)
  const [modesLoading, setModesLoading] = useState(false)

  const corridors = useApiData(() => api.getCorridors(), { refreshInterval: 300000 })

  const handleSelect = useCallback(async (c: Corridor) => {
    setSelected(c)
    setModesLoading(true)
    try {
      const res = await api.getCorridorModes(c.corridor_id)
      if (res.data) setModeData(res.data)
    } catch { /* ignore */ }
    setModesLoading(false)
  }, [])

  if (corridors.loading) return <LoadingSpinner message="Loading corridors…" />

  return (
    <div className="flex h-full">
      <main className="relative flex-1">
        {corridors.error && <div className="absolute left-4 top-4 z-[1000]"><ErrorBanner message={corridors.error} onRetry={corridors.refresh} /></div>}
        <FreightMap
          corridors={corridors.data ?? []}
          onCorridorSelect={handleSelect}
          selectedCorridorId={selected?.corridor_id}
        />
      </main>

      <aside className="w-96 overflow-y-auto border-l border-border bg-card p-4">
        <h2 className="mb-4 text-lg font-semibold text-foreground">US Freight Corridors</h2>

        {/* Corridor summary */}
        <div className="mb-4 rounded-lg bg-background p-3 text-xs">
          <div className="mb-2 text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
            Network Overview
          </div>
          <div className="flex justify-between gap-2">
            <div className="text-center">
              <div className="text-lg font-bold text-primary">{corridors.data?.length ?? 0}</div>
              <div className="text-muted-foreground">corridors</div>
            </div>
            <div className="text-center">
              <div className="text-lg font-bold" style={{ color: chartColors.orange }}>
                {fmt(corridors.data?.reduce((sum, c) => sum + (c.total_tons ?? 0), 0))}
              </div>
              <div className="text-muted-foreground">total tons</div>
            </div>
            <div className="text-center">
              <div className="text-lg font-bold" style={{ color: chartColors.green }}>
                ${fmt(corridors.data?.reduce((sum, c) => sum + (c.total_value_usd ?? 0), 0))}
              </div>
              <div className="text-muted-foreground">total value</div>
            </div>
          </div>
        </div>

        {/* Corridor list */}
        <div className="mb-4 flex flex-col gap-2">
          {(corridors.data ?? []).map(c => (
            <button
              key={c.corridor_id}
              onClick={() => handleSelect(c)}
              className={`rounded-lg border p-3 text-left text-sm transition-colors ${
                selected?.corridor_id === c.corridor_id
                  ? 'border-primary bg-secondary'
                  : 'border-border bg-background hover:bg-secondary/50'
              }`}
            >
              <div className="mb-1 font-semibold text-foreground">{c.name}</div>
              {c.description && <div className="mb-1 text-[11px] text-muted-foreground">{c.description}</div>}
              <div className="flex gap-3 text-[11px] text-muted-foreground">
                <span>{fmt(c.total_tons)} tons</span>
                <span>${fmt(c.total_value_usd)}</span>
                {c.estimated_cost != null && <span>Cost: ${fmt(c.estimated_cost)}</span>}
              </div>
            </button>
          ))}
        </div>

        {/* Selected corridor detail */}
        {selected && (
          <Card>
            <CardHeader>
              <CardTitle className="text-sm">{selected.name}</CardTitle>
            </CardHeader>
            <CardContent>
              <table className="w-full border-collapse text-sm">
                <tbody>
                  {([
                    ['Total Tons', fmt(selected.total_tons)],
                    ['Total Value', selected.total_value_usd != null ? `$${fmt(selected.total_value_usd)}` : '—'],
                    ['Ton-Miles', fmt(selected.total_ton_miles)],
                    ['Est. Cost', selected.estimated_cost != null ? `$${fmt(selected.estimated_cost)}` : '—'],
                    ['Cost/Ton', selected.cost_per_ton != null ? `$${selected.cost_per_ton.toFixed(2)}` : '—'],
                    ['Year', selected.year?.toString() ?? '—'],
                  ] as [string, string][]).map(([label, value]) => (
                    <tr key={label} className="border-b border-border">
                      <td className="w-28 py-1.5 text-muted-foreground">{label}</td>
                      <td className="py-1.5 text-foreground">{value}</td>
                    </tr>
                  ))}
                </tbody>
              </table>

              {/* Mode breakdown */}
              {modesLoading && <div className="mt-3 text-xs text-muted-foreground">Loading modes…</div>}
              {modeData && modeData.modes && (
                <div className="mt-3">
                  <div className="mb-2 text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                    Mode Breakdown
                  </div>
                  <div className="flex flex-col gap-1.5">
                    {modeData.modes.map(m => (
                      <div key={m.mode_code} className="flex items-center justify-between text-xs">
                        <span className="text-foreground">{m.mode_name}</span>
                        <div className="flex gap-3 text-muted-foreground">
                          <span>{fmt(m.tons_thousands)}K tons</span>
                          <span>${m.cost_per_ton_mile.toFixed(3)}/tm</span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        )}

        {!selected && (
          <p className="text-sm text-muted-foreground">Click a corridor on the map to see details.</p>
        )}
      </aside>
    </div>
  )
}
