'use client'

import { useState, useMemo } from 'react'
import { api } from '@/lib/api'
import { useApiData } from '@/hooks/useApiData'
import { Card, CardHeader, CardTitle, CardContent, DataTable, LoadingSpinner, ErrorBanner, StatusBadge, Button } from '@/components/ui'
import { cn } from '@/lib/utils'
import type { SchedulePattern, ImputedFlight } from '@/types'

const DAY_NAMES = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
const TIME_SLOTS = [
  '04:00–06:00', '06:00–08:00', '08:00–10:00', '10:00–12:00',
  '12:00–14:00', '14:00–16:00', '16:00–18:00', '18:00–20:00',
  '20:00–22:00', '22:00–00:00',
]

const STATUS_COLORS: Record<string, string> = {
  expected: '#38bdf8',
  confirmed: '#22c55e',
  missed: '#ef4444',
}

type StatusFilter = 'all' | 'expected' | 'confirmed' | 'missed'

export default function SchedulePage() {
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('all')
  const [running, setRunning] = useState(false)

  const patterns = useApiData(() => api.getSchedulePatterns(), { refreshInterval: 60000 })
  const imputed = useApiData(() => api.getImputedFlights(
    statusFilter === 'all' ? undefined : statusFilter, 200,
  ), { refreshInterval: 30000 })

  const allImputed = useApiData(() => api.getImputedFlights(undefined, 1000))

  const summary = useMemo(() => {
    const flights = allImputed.data ?? []
    const today = new Date().toISOString().slice(0, 10)
    const todayFlights = flights.filter(f => f.expected_departure?.startsWith(today))
    return {
      totalPatterns: patterns.data?.length ?? 0,
      expected: todayFlights.filter(f => f.status === 'expected').length,
      confirmed: todayFlights.filter(f => f.status === 'confirmed').length,
      missed: todayFlights.filter(f => f.status === 'missed').length,
    }
  }, [patterns.data, allImputed.data])

  const grid = useMemo(() => {
    if (!patterns.data) return null
    const cells: Record<string, SchedulePattern[]> = {}
    for (const p of patterns.data) {
      const hour = parseInt(p.typical_departure_utc?.slice(0, 2) ?? '0', 10)
      const slotIdx = Math.max(0, Math.min(TIME_SLOTS.length - 1, Math.floor((hour - 4) / 2)))
      const key = `${p.day_of_week}-${slotIdx}`
      if (!cells[key]) cells[key] = []
      cells[key].push(p)
    }
    return cells
  }, [patterns.data])

  const handleRun = async () => {
    setRunning(true)
    try {
      await api.triggerImputationCycle()
      patterns.refresh()
      imputed.refresh()
      allImputed.refresh()
    } catch { /* ignore */ }
    setRunning(false)
  }

  if (patterns.loading && imputed.loading) return <LoadingSpinner message="Loading schedule data…" />

  return (
    <div className="mx-auto max-w-[1400px] overflow-y-auto p-5 h-full">
      <div className="mb-5 flex items-center justify-between">
        <h1 className="text-xl font-bold text-foreground">
          Flight Schedule Intelligence
        </h1>
        <Button onClick={handleRun} disabled={running}>
          {running ? 'Running…' : 'Run Imputation'}
        </Button>
      </div>

      {(patterns.error || imputed.error) && (
        <ErrorBanner
          message={patterns.error || imputed.error || 'Failed to load schedule data'}
          onRetry={() => { patterns.refresh(); imputed.refresh() }}
        />
      )}

      {/* Summary Cards */}
      <div className="mb-6 grid grid-cols-[repeat(auto-fill,minmax(180px,1fr))] gap-3">
        <SummaryCard label="Patterns Learned" value={summary.totalPatterns} color="#38bdf8" />
        <SummaryCard label="Expected Today" value={summary.expected} color="#f59e0b" />
        <SummaryCard label="Confirmed Today" value={summary.confirmed} color="#22c55e" />
        <SummaryCard label="Missed Today" value={summary.missed} color="#ef4444" />
      </div>

      {/* Weekly Schedule Grid */}
      <Card className="mb-6">
        <CardHeader>
          <CardTitle>Weekly Schedule Heatmap</CardTitle>
        </CardHeader>
        <CardContent>
          {grid ? (
            <div className="overflow-x-auto">
              <div className="grid grid-cols-[100px_repeat(7,1fr)] gap-0.5 min-w-[700px]">
                {/* Header row */}
                <div />
                {DAY_NAMES.map(d => (
                  <div key={d} className="text-center text-xs font-semibold text-muted-foreground py-1.5">
                    {d}
                  </div>
                ))}
                {/* Time rows */}
                {TIME_SLOTS.map((slot, slotIdx) => (
                  <div key={`row-${slotIdx}`} className="contents">
                    <div className="flex items-center text-[11px] text-muted-foreground px-1 py-2">
                      {slot}
                    </div>
                    {Array.from({ length: 7 }, (_, dow) => {
                      const key = `${dow}-${slotIdx}`
                      const cell = grid[key] ?? []
                      const intensity = Math.min(1, cell.length / 8)
                      return (
                        <div
                          key={key}
                          className="rounded min-h-9 px-1.5 py-1 text-[11px] text-foreground"
                          style={{
                            background: cell.length > 0
                              ? `rgba(56, 189, 248, ${0.08 + intensity * 0.35})`
                              : 'rgba(255,255,255,0.02)',
                          }}
                          title={cell.map(p => `${p.callsign} ${p.origin_icao ?? '?'}→${p.destination_icao ?? '?'}`).join('\n')}
                        >
                          {cell.length > 0 && (
                            <span className="font-semibold text-[13px]">{cell.length}</span>
                          )}
                          {cell.length > 0 && cell.length <= 3 && (
                            <div className="text-muted-foreground text-[10px] mt-0.5">
                              {cell.slice(0, 3).map(p => p.callsign).join(', ')}
                            </div>
                          )}
                        </div>
                      )
                    })}
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <div className="p-5 text-center text-sm text-muted-foreground">
              No schedule patterns learned yet. Data collection must run for a few days.
            </div>
          )}
        </CardContent>
      </Card>

      {/* Imputed Flights Table */}
      <Card>
        <CardHeader>
          <CardTitle>Imputed Flights</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="mb-3 flex gap-1.5">
            {(['all', 'expected', 'confirmed', 'missed'] as StatusFilter[]).map(f => (
              <Button
                key={f}
                variant={statusFilter === f ? 'default' : 'outline'}
                size="sm"
                onClick={() => setStatusFilter(f)}
                className="capitalize"
              >
                {f}
              </Button>
            ))}
          </div>

          <DataTable<ImputedFlight & Record<string, unknown>>
            columns={[
              { key: 'callsign', label: 'Callsign' },
              {
                key: 'expected_departure',
                label: 'Expected Departure',
                render: (r) => r.expected_departure
                  ? new Date(r.expected_departure).toLocaleString()
                  : '—',
              },
              {
                key: 'route',
                label: 'Route',
                render: (r) => `${r.origin_icao ?? '?'} → ${r.destination_icao ?? '?'}`,
              },
              {
                key: 'status',
                label: 'Status',
                render: (r) => (
                  <StatusBadge label={r.status} color={STATUS_COLORS[r.status] ?? '#94a3b8'} />
                ),
              },
              {
                key: 'confidence',
                label: 'Confidence',
                align: 'right',
                render: (r) => `${(r.confidence * 100).toFixed(0)}%`,
              },
            ]}
            data={(imputed.data ?? []) as (ImputedFlight & Record<string, unknown>)[]}
            emptyMessage="No imputed flights found"
            maxRows={100}
          />
        </CardContent>
      </Card>
    </div>
  )
}

function SummaryCard({ label, value, color }: { label: string; value: number; color: string }) {
  return (
    <Card>
      <CardContent className="pt-4">
        <div className="text-[11px] font-medium uppercase tracking-wider text-muted-foreground">
          {label}
        </div>
        <div className="mt-1 text-[28px] font-bold" style={{ color }}>
          {value.toLocaleString()}
        </div>
      </CardContent>
    </Card>
  )
}
