'use client'

import dynamic from 'next/dynamic'
import { useState } from 'react'
import { api } from '@/lib/api'
import { useApiData } from '@/hooks/useApiData'
import { ErrorBanner } from '@/components/ui'
import type { StateVector } from '@/types'

const FlightMap = dynamic(() => import('@/components/Map/FlightMap'), { ssr: false })

export default function DashboardPage() {
  const [selectedFlight, setSelectedFlight] = useState<StateVector | null>(null)
  const emissions = useApiData(() => api.getEmissions(), { refreshInterval: 15000 })

  const e = emissions.data

  return (
    <div className="flex h-full">
      <main className="relative flex-1">
        <FlightMap onFlightSelect={setSelectedFlight} />
      </main>

      <aside className="w-80 overflow-y-auto border-l border-border bg-card p-4">
        <h2 className="mb-4 text-lg font-semibold text-foreground">SWISS Flight Tracker</h2>

        {/* Fleet summary strip */}
        <div className="mb-4 rounded-lg bg-background p-3 text-xs">
          <div className="mb-2 text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
            SWISS Fleet (last 10 min)
          </div>
          {emissions.error && <ErrorBanner message={emissions.error} onRetry={emissions.refresh} />}
          <div className="flex justify-between gap-2">
            <div className="text-center">
              <div className="text-lg font-bold text-primary">{e?.aircraft_count ?? '—'}</div>
              <div className="text-muted-foreground">aircraft</div>
            </div>
            <div className="text-center">
              <div className="text-lg font-bold text-warning">
                {e ? e.total_fuel_kg_s.toFixed(1) : '—'}
              </div>
              <div className="text-muted-foreground">kg/s fuel</div>
            </div>
            <div className="text-center">
              <div className="text-lg font-bold text-danger">
                {e ? e.total_co2_kg_s.toFixed(1) : '—'}
              </div>
              <div className="text-muted-foreground">kg/s CO₂</div>
            </div>
          </div>
        </div>

        {selectedFlight ? (
          <div>
            <h3 className="mb-2 text-primary font-semibold">
              {selectedFlight.callsign ?? selectedFlight.icao24}
            </h3>
            <table className="w-full border-collapse text-sm">
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
                  <tr key={label} className="border-b border-border">
                    <td className="w-24 py-1.5 text-muted-foreground">{label}</td>
                    <td className="py-1.5 text-foreground">{value}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="text-sm text-muted-foreground">Click an aircraft on the map to see details.</p>
        )}
      </aside>
    </div>
  )
}
