'use client'

import { useEffect, useRef } from 'react'
import 'leaflet/dist/leaflet.css'
import type { StateVector } from '@/types'
import { createFlightSocket } from '@/lib/websocket'

interface Props {
  onFlightSelect: (flight: StateVector) => void
}

const planeSvg = (size: number) =>
  `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="black" width="${size}" height="${size}">
    <path d="M21 16v-2l-8-5V3.5c0-.83-.67-1.5-1.5-1.5S10 2.67 10 3.5V9l-8 5v2l8-2.5V19l-2 1.5V22l3.5-1 3.5 1v-1.5L13 19v-5.5l8 2.5z"/>
  </svg>`

const ICON_PX = 20

export default function FlightMap({ onFlightSelect }: Props) {
  const containerRef = useRef<HTMLDivElement>(null)
  const mapRef = useRef<import('leaflet').Map | null>(null)
  const markersRef = useRef<Map<string, import('leaflet').Marker>>(new Map())
  const onFlightSelectRef = useRef(onFlightSelect)
  const flightDataRef = useRef<Map<string, StateVector>>(new Map())
  const headingRef = useRef<Map<string, number | null>>(new Map())

  useEffect(() => {
    onFlightSelectRef.current = onFlightSelect
  })

  useEffect(() => {
    if (!containerRef.current) return

    let cancelled = false
    let ws: WebSocket | null = null

    import('leaflet').then((L) => {
      if (cancelled || mapRef.current) return
      const map = L.map(containerRef.current!).setView([46.8, 8.2], 8)
      mapRef.current = map

      L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
        maxZoom: 18,
      }).addTo(map)

      const planeIcon = (heading: number | null) =>
        L.divIcon({
          html: `<div style="transform:rotate(${heading ?? 0}deg);width:${ICON_PX}px;height:${ICON_PX}px;">${planeSvg(ICON_PX)}</div>`,
          className: '',
          iconSize: [ICON_PX, ICON_PX],
          iconAnchor: [ICON_PX / 2, ICON_PX / 2],
        })

      const updateMarkers = (flights: StateVector[]) => {
        const seen = new Set<string>()

        for (const flight of flights) {
          if (flight.latitude == null || flight.longitude == null) continue
          seen.add(flight.icao24)

          flightDataRef.current.set(flight.icao24, flight)

          const existing = markersRef.current.get(flight.icao24)
          if (existing) {
            existing.setLatLng([flight.latitude, flight.longitude])
            // Only redraw icon when heading changes by more than 5°
            const prevHeading = headingRef.current.get(flight.icao24)
            if (prevHeading === undefined || Math.abs((prevHeading ?? 0) - (flight.heading ?? 0)) > 5) {
              existing.setIcon(planeIcon(flight.heading))
              headingRef.current.set(flight.icao24, flight.heading)
            }
          } else {
            const marker = L.marker([flight.latitude, flight.longitude], { icon: planeIcon(flight.heading) })
              .addTo(map)
              .on('click', () => {
                const latest = flightDataRef.current.get(flight.icao24) ?? flight
                onFlightSelectRef.current(latest)
              })
            markersRef.current.set(flight.icao24, marker)
            headingRef.current.set(flight.icao24, flight.heading)
          }
        }

        // Remove stale markers
        for (const [icao24, marker] of markersRef.current) {
          if (!seen.has(icao24)) {
            marker.remove()
            markersRef.current.delete(icao24)
            headingRef.current.delete(icao24)
          }
        }
      }

      ws = createFlightSocket(updateMarkers)
    })

    return () => {
      cancelled = true
      ws?.close()
      mapRef.current?.remove()
      mapRef.current = null
      markersRef.current.clear()
      flightDataRef.current.clear()
      headingRef.current.clear()
    }
  }, [])

  return <div ref={containerRef} style={{ height: '100%', width: '100%' }} />
}
