'use client'

import { useEffect, useRef, useState } from 'react'
import 'leaflet/dist/leaflet.css'
import type { StateVector } from '@/types'
import { createFlightSocket } from '@/lib/websocket'

const API = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'

interface Props {
  onFlightSelect: (flight: StateVector) => void
}

const planeSvg = (size: number, fill: string) =>
  `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="${fill}" width="${size}" height="${size}">
    <path d="M21 16v-2l-8-5V3.5c0-.83-.67-1.5-1.5-1.5S10 2.67 10 3.5V9l-8 5v2l8-2.5V19l-2 1.5V22l3.5-1 3.5 1v-1.5L13 19v-5.5l8 2.5z"/>
  </svg>`

const ICON_PX = 20

// Cache icon HTML strings to avoid regenerating SVG on every update
// Key: `${roundedHeading}_${isSelected}`
const iconHtmlCache = new Map<string, string>()
function getIconHtml(heading: number | null, isSelected: boolean): string {
  const rounded = Math.round((heading ?? 0) / 5) * 5
  const key = `${rounded}_${isSelected ? 1 : 0}`
  let html = iconHtmlCache.get(key)
  if (!html) {
    html = `<div style="transform:rotate(${rounded}deg);width:${ICON_PX}px;height:${ICON_PX}px;">${planeSvg(ICON_PX, isSelected ? '#000000' : '#dc0018')}</div>`
    iconHtmlCache.set(key, html)
  }
  return html
}

export default function FlightMap({ onFlightSelect }: Props) {
  const containerRef = useRef<HTMLDivElement>(null)
  const mapRef = useRef<import('leaflet').Map | null>(null)
  const markersRef = useRef<Map<string, import('leaflet').Marker>>(new Map())
  const onFlightSelectRef = useRef(onFlightSelect)
  const flightDataRef = useRef<Map<string, StateVector>>(new Map())
  const headingRef = useRef<Map<string, number | null>>(new Map())
  const selectedRef = useRef<string | null>(null)
  const leafletRef = useRef<typeof import('leaflet') | null>(null)
  const [selectedIcao, setSelectedIcao] = useState<string | null>(null)

  useEffect(() => {
    onFlightSelectRef.current = onFlightSelect
  })

  useEffect(() => {
    if (!containerRef.current) return

    let cancelled = false
    let ws: WebSocket | null = null
    let pollInterval: ReturnType<typeof setInterval> | null = null

    import('leaflet').then((L) => {
      if (cancelled || mapRef.current) return
      leafletRef.current = L
      const map = L.map(containerRef.current!).setView([47.4, 8.5], 5)
      mapRef.current = map

      L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
        maxZoom: 18,
      }).addTo(map)

      const planeIcon = (heading: number | null, isSelected: boolean) =>
        L.divIcon({
          html: getIconHtml(heading, isSelected),
          className: '',
          iconSize: [ICON_PX, ICON_PX],
          iconAnchor: [ICON_PX / 2, ICON_PX / 2],
        })

      const updateMarkers = (flights: StateVector[]) => {
        // Skip DOM updates when tab is hidden
        if (document.hidden) {
          for (const f of flights) flightDataRef.current.set(f.icao24, f)
          return
        }

        const seen = new Set<string>()

        for (const flight of flights) {
          if (flight.latitude == null || flight.longitude == null) continue
          seen.add(flight.icao24)

          flightDataRef.current.set(flight.icao24, flight)
          const isSelected = flight.icao24 === selectedRef.current

          const existing = markersRef.current.get(flight.icao24)
          if (existing) {
            existing.setLatLng([flight.latitude, flight.longitude])
            const prevHeading = headingRef.current.get(flight.icao24)
            if (prevHeading === undefined || Math.abs((prevHeading ?? 0) - (flight.heading ?? 0)) > 5) {
              existing.setIcon(planeIcon(flight.heading, isSelected))
              headingRef.current.set(flight.icao24, flight.heading)
            }
          } else {
            const marker = L.marker([flight.latitude, flight.longitude], { icon: planeIcon(flight.heading, isSelected) })
              .addTo(map)
              .on('click', () => {
                const prev = selectedRef.current
                selectedRef.current = flight.icao24
                setSelectedIcao(flight.icao24)

                // Update previous selected marker back to red
                if (prev && prev !== flight.icao24) {
                  const prevMarker = markersRef.current.get(prev)
                  if (prevMarker) {
                    prevMarker.setIcon(planeIcon(headingRef.current.get(prev) ?? null, false))
                  }
                }
                // Update newly selected marker to black
                marker.setIcon(planeIcon(flight.heading, true))

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

      // Primary: WebSocket for real-time updates
      ws = createFlightSocket(updateMarkers)

      // Fallback: REST polling every 10s (works when WebSocket or Redis are unavailable)
      const pollRest = async () => {
        if (document.hidden) return
        try {
          const res = await fetch(`${API}/flights/live`)
          const json = await res.json()
          if (json.data?.length > 0) {
            updateMarkers(json.data)
          }
        } catch { /* best-effort */ }
      }
      // Initial fetch to populate markers immediately
      pollRest()
      pollInterval = setInterval(pollRest, 10_000)
    })

    return () => {
      cancelled = true
      ws?.close()
      if (pollInterval) clearInterval(pollInterval)
      mapRef.current?.remove()
      mapRef.current = null
      markersRef.current.clear()
      flightDataRef.current.clear()
      headingRef.current.clear()
      leafletRef.current = null
    }
  }, [])

  // Update selected marker icon when selection changes externally
  useEffect(() => {
    const L = leafletRef.current
    if (!L) return

    const planeIcon = (heading: number | null, isSelected: boolean) =>
      L.divIcon({
        html: getIconHtml(heading, isSelected),
        className: '',
        iconSize: [ICON_PX, ICON_PX],
        iconAnchor: [ICON_PX / 2, ICON_PX / 2],
      })

    for (const [icao24, marker] of markersRef.current) {
      const isSelected = icao24 === selectedIcao
      marker.setIcon(planeIcon(headingRef.current.get(icao24) ?? null, isSelected))
    }
  }, [selectedIcao])

  return <div ref={containerRef} style={{ height: '100%', width: '100%' }} />
}
