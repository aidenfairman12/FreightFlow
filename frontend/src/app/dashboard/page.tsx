'use client'

import dynamic from 'next/dynamic'
import { useState, useEffect } from 'react'
import type { StateVector } from '@/types'

// Leaflet must be loaded client-side only — no SSR
const FlightMap = dynamic(() => import('@/components/Map/FlightMap'), { ssr: false })

interface EmissionsSummary {
  aircraft_count: number
  total_fuel_kg_s: number
  total_co2_kg_s: number
}

export default function DashboardPage() {
  const [selectedFlight, setSelectedFlight] = useState<StateVector | null>(null)
  const [emissions, setEmissions] = useState<EmissionsSummary | null>(null)

  useEffect(() => {
    const fetchEmissions = async () => {
      try {
        const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/analytics/emissions`)
        const json = await res.json()
        if (json.data) setEmissions(json.data)
      } catch {
        // silently ignore — summary is best-effort
      }
    }
    fetchEmissions()
    const interval = setInterval(fetchEmissions, 15000)
    return () => clearInterval(interval)
  }, [])

  return (
    <div style={{ display: 'flex', height: '100vh' }}>
      <main style={{ flex: 1, position: 'relative' }}>
        <FlightMap onFlightSelect={setSelectedFlight} />
      </main>

      <aside style={{ width: 320, padding: 16, overflowY: 'auto', background: '#1e293b', borderLeft: '1px solid #334155' }}>
        <h2 style={{ margin: '0 0 16px', fontSize: 18, fontWeight: 600 }}>PlaneLogistics</h2>

        {/* Fleet summary strip */}
        <div style={{ background: '#0f172a', borderRadius: 8, padding: '10px 12px', marginBottom: 16, fontSize: 12 }}>
          <div style={{ color: '#94a3b8', marginBottom: 6, fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.05em' }}>Fleet (last 10 min)</div>
          <div style={{ display: 'flex', justifyContent: 'space-between', gap: 8 }}>
            <div style={{ textAlign: 'center' }}>
              <div style={{ fontSize: 18, fontWeight: 700, color: '#38bdf8' }}>{emissions?.aircraft_count ?? '—'}</div>
              <div style={{ color: '#64748b' }}>aircraft</div>
            </div>
            <div style={{ textAlign: 'center' }}>
              <div style={{ fontSize: 18, fontWeight: 700, color: '#f59e0b' }}>
                {emissions ? emissions.total_fuel_kg_s.toFixed(1) : '—'}
              </div>
              <div style={{ color: '#64748b' }}>kg/s fuel</div>
            </div>
            <div style={{ textAlign: 'center' }}>
              <div style={{ fontSize: 18, fontWeight: 700, color: '#ef4444' }}>
                {emissions ? emissions.total_co2_kg_s.toFixed(1) : '—'}
              </div>
              <div style={{ color: '#64748b' }}>kg/s CO₂</div>
            </div>
          </div>
        </div>

        {selectedFlight ? (
          <div>
            <h3 style={{ margin: '0 0 8px', color: '#38bdf8' }}>
              {selectedFlight.callsign ?? selectedFlight.icao24}
            </h3>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
              <tbody>
                {[
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
                ].map(([label, value]) => (
                  <tr key={label} style={{ borderBottom: '1px solid #334155' }}>
                    <td style={{ padding: '6px 0', color: '#94a3b8', width: 90 }}>{label}</td>
                    <td style={{ padding: '6px 0' }}>{value}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p style={{ color: '#64748b', fontSize: 14 }}>Click an aircraft on the map to see details.</p>
        )}
      </aside>
    </div>
  )
}
