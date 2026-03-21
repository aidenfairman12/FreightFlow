'use client'

import dynamic from 'next/dynamic'
import { useState } from 'react'
import { api } from '@/lib/api'
import { useApiData } from '@/hooks/useApiData'
import { ErrorBanner } from '@/components/ui'
import { colors } from '@/styles/theme'
import type { StateVector } from '@/types'

const FlightMap = dynamic(() => import('@/components/Map/FlightMap'), { ssr: false })

export default function DashboardPage() {
  const [selectedFlight, setSelectedFlight] = useState<StateVector | null>(null)
  const emissions = useApiData(() => api.getEmissions(), { refreshInterval: 15000 })

  const e = emissions.data

  return (
    <div style={{ display: 'flex', height: '100%' }}>
      <main style={{ flex: 1, position: 'relative' }}>
        <FlightMap onFlightSelect={setSelectedFlight} />
      </main>

      <aside style={{ width: 320, padding: 16, overflowY: 'auto', background: colors.card, borderLeft: `1px solid ${colors.border}` }}>
        <h2 style={{ margin: '0 0 16px', fontSize: 18, fontWeight: 600, color: colors.text }}>SWISS Flight Tracker</h2>

        {/* Fleet summary strip */}
        <div style={{ background: colors.bg, borderRadius: 8, padding: '10px 12px', marginBottom: 16, fontSize: 12 }}>
          <div style={{ color: colors.textMuted, marginBottom: 6, fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
            SWISS Fleet (last 10 min)
          </div>
          {emissions.error && <ErrorBanner message={emissions.error} onRetry={emissions.refresh} />}
          <div style={{ display: 'flex', justifyContent: 'space-between', gap: 8 }}>
            <div style={{ textAlign: 'center' }}>
              <div style={{ fontSize: 18, fontWeight: 700, color: colors.accent }}>{e?.aircraft_count ?? '—'}</div>
              <div style={{ color: colors.textDim }}>aircraft</div>
            </div>
            <div style={{ textAlign: 'center' }}>
              <div style={{ fontSize: 18, fontWeight: 700, color: colors.orange }}>
                {e ? e.total_fuel_kg_s.toFixed(1) : '—'}
              </div>
              <div style={{ color: colors.textDim }}>kg/s fuel</div>
            </div>
            <div style={{ textAlign: 'center' }}>
              <div style={{ fontSize: 18, fontWeight: 700, color: colors.red }}>
                {e ? e.total_co2_kg_s.toFixed(1) : '—'}
              </div>
              <div style={{ color: colors.textDim }}>kg/s CO₂</div>
            </div>
          </div>
        </div>

        {selectedFlight ? (
          <div>
            <h3 style={{ margin: '0 0 8px', color: colors.accent }}>
              {selectedFlight.callsign ?? selectedFlight.icao24}
            </h3>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
              <tbody>
                {([
                  ['ICAO24', selectedFlight.icao24],
                  ['Aircraft', selectedFlight.aircraft_type ?? '—'],
                  ['Airline', selectedFlight.airline_name ?? '—'],
                  ['Origin', selectedFlight.origin_airport ?? '—'],
                  ['Destination', selectedFlight.destination_airport ?? '—'],
                  ['Altitude', selectedFlight.baro_altitude != null ? `${Math.round(selectedFlight.baro_altitude)} m` : '—'],
                  ['Speed', selectedFlight.velocity != null ? `${Math.round(selectedFlight.velocity)} m/s` : '—'],
                  ['Heading', selectedFlight.heading != null ? `${Math.round(selectedFlight.heading)}°` : '—'],
                  ['Fuel rate', selectedFlight.fuel_flow_kg_s != null ? `${selectedFlight.fuel_flow_kg_s.toFixed(2)} kg/s` : '—'],
                  ['CO₂ rate', selectedFlight.co2_kg_s != null ? `${selectedFlight.co2_kg_s.toFixed(2)} kg/s` : '—'],
                  ['On ground', selectedFlight.on_ground ? 'Yes' : 'No'],
                ] as [string, string][]).map(([label, value]) => (
                  <tr key={label} style={{ borderBottom: `1px solid ${colors.border}` }}>
                    <td style={{ padding: '6px 0', color: colors.textMuted, width: 90 }}>{label}</td>
                    <td style={{ padding: '6px 0', color: colors.text }}>{value}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p style={{ color: colors.textDim, fontSize: 14 }}>Click an aircraft on the map to see details.</p>
        )}
      </aside>
    </div>
  )
}
