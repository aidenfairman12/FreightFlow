'use client'

import { useState, useMemo } from 'react'
import { api } from '@/lib/api'
import { useApiData } from '@/hooks/useApiData'
import { Card, DataTable, LoadingSpinner, ErrorBanner, StatusBadge } from '@/components/ui'
import { colors, buttonStyle, buttonPrimaryStyle } from '@/styles/theme'
import type { SchedulePattern, ImputedFlight } from '@/types'

const DAY_NAMES = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
const TIME_SLOTS = [
  '04:00–06:00', '06:00–08:00', '08:00–10:00', '10:00–12:00',
  '12:00–14:00', '14:00–16:00', '16:00–18:00', '18:00–20:00',
  '20:00–22:00', '22:00–00:00',
]

const STATUS_COLORS: Record<string, string> = {
  expected: colors.accent,
  confirmed: colors.green,
  missed: colors.red,
}

type StatusFilter = 'all' | 'expected' | 'confirmed' | 'missed'

export default function SchedulePage() {
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('all')
  const [running, setRunning] = useState(false)

  const patterns = useApiData(() => api.getSchedulePatterns(), { refreshInterval: 60000 })
  const imputed = useApiData(() => api.getImputedFlights(
    statusFilter === 'all' ? undefined : statusFilter, 200,
  ), { refreshInterval: 30000 })

  // Recount by status from all imputed flights (fetch all for summary)
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

  // Build weekly schedule grid
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
    <div style={{ padding: 20, maxWidth: 1400, margin: '0 auto' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
        <h1 style={{ fontSize: 20, fontWeight: 700, color: colors.text, margin: 0 }}>
          Flight Schedule Intelligence
        </h1>
        <button
          onClick={handleRun}
          disabled={running}
          style={{ ...buttonPrimaryStyle, opacity: running ? 0.6 : 1 }}
        >
          {running ? 'Running…' : 'Run Imputation'}
        </button>
      </div>

      {(patterns.error || imputed.error) && (
        <ErrorBanner
          message={patterns.error || imputed.error || 'Failed to load schedule data'}
          onRetry={() => { patterns.refresh(); imputed.refresh() }}
        />
      )}

      {/* Summary Cards */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fill, minmax(180px, 1fr))',
        gap: 12,
        marginBottom: 24,
      }}>
        <SummaryCard label="Patterns Learned" value={summary.totalPatterns} color={colors.accent} />
        <SummaryCard label="Expected Today" value={summary.expected} color={colors.orange} />
        <SummaryCard label="Confirmed Today" value={summary.confirmed} color={colors.green} />
        <SummaryCard label="Missed Today" value={summary.missed} color={colors.red} />
      </div>

      {/* Weekly Schedule Grid */}
      <Card title="Weekly Schedule Heatmap" style={{ marginBottom: 24 }}>
        {grid ? (
          <div style={{ overflowX: 'auto' }}>
            <div style={{
              display: 'grid',
              gridTemplateColumns: '100px repeat(7, 1fr)',
              gap: 2,
              minWidth: 700,
            }}>
              {/* Header row */}
              <div />
              {DAY_NAMES.map(d => (
                <div key={d} style={{
                  textAlign: 'center', fontSize: 12, fontWeight: 600,
                  color: colors.textMuted, padding: '6px 0',
                }}>
                  {d}
                </div>
              ))}
              {/* Time rows */}
              {TIME_SLOTS.map((slot, slotIdx) => (
                <>
                  <div key={`label-${slotIdx}`} style={{
                    fontSize: 11, color: colors.textDim, padding: '8px 4px',
                    display: 'flex', alignItems: 'center',
                  }}>
                    {slot}
                  </div>
                  {Array.from({ length: 7 }, (_, dow) => {
                    const key = `${dow}-${slotIdx}`
                    const cell = grid[key] ?? []
                    const intensity = Math.min(1, cell.length / 8)
                    return (
                      <div
                        key={key}
                        style={{
                          background: cell.length > 0
                            ? `rgba(56, 189, 248, ${0.08 + intensity * 0.35})`
                            : `rgba(255,255,255,0.02)`,
                          borderRadius: 4,
                          padding: '4px 6px',
                          minHeight: 36,
                          fontSize: 11,
                          color: colors.text,
                        }}
                        title={cell.map(p => `${p.callsign} ${p.origin_icao ?? '?'}→${p.destination_icao ?? '?'}`).join('\n')}
                      >
                        {cell.length > 0 && (
                          <span style={{ fontWeight: 600, fontSize: 13 }}>{cell.length}</span>
                        )}
                        {cell.length > 0 && cell.length <= 3 && (
                          <div style={{ color: colors.textMuted, fontSize: 10, marginTop: 2 }}>
                            {cell.slice(0, 3).map(p => p.callsign).join(', ')}
                          </div>
                        )}
                      </div>
                    )
                  })}
                </>
              ))}
            </div>
          </div>
        ) : (
          <div style={{ color: colors.textDim, fontSize: 13, padding: 20, textAlign: 'center' }}>
            No schedule patterns learned yet. Data collection must run for a few days.
          </div>
        )}
      </Card>

      {/* Imputed Flights Table */}
      <Card title="Imputed Flights">
        <div style={{ display: 'flex', gap: 6, marginBottom: 12 }}>
          {(['all', 'expected', 'confirmed', 'missed'] as StatusFilter[]).map(f => (
            <button
              key={f}
              onClick={() => setStatusFilter(f)}
              style={{
                ...buttonStyle,
                background: statusFilter === f ? colors.accent : colors.card,
                color: statusFilter === f ? colors.bg : colors.text,
                fontWeight: statusFilter === f ? 600 : 400,
                textTransform: 'capitalize',
              }}
            >
              {f}
            </button>
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
                <StatusBadge label={r.status} color={STATUS_COLORS[r.status] ?? colors.textMuted} />
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
      </Card>
    </div>
  )
}

function SummaryCard({ label, value, color }: { label: string; value: number; color: string }) {
  return (
    <Card>
      <div style={{ fontSize: 11, color: colors.textMuted, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
        {label}
      </div>
      <div style={{ fontSize: 28, fontWeight: 700, color, marginTop: 4 }}>
        {value.toLocaleString()}
      </div>
    </Card>
  )
}
