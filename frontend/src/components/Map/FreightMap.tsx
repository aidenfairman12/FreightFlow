'use client'

import { useEffect, useRef } from 'react'
import 'leaflet/dist/leaflet.css'
import type { Corridor } from '@/types'

const MODE_COLORS: Record<string, string> = {
  truck: '#ef4444',
  rail: '#3b82f6',
  water: '#06b6d4',
  air: '#f59e0b',
  intermodal: '#a78bfa',
}

interface Props {
  corridors: Corridor[]
  onCorridorSelect: (corridor: Corridor) => void
  selectedCorridorId?: string | null
}

export default function FreightMap({ corridors, onCorridorSelect, selectedCorridorId }: Props) {
  const containerRef = useRef<HTMLDivElement>(null)
  const mapRef = useRef<import('leaflet').Map | null>(null)
  const layersRef = useRef<import('leaflet').LayerGroup | null>(null)

  // Initialize map once
  useEffect(() => {
    if (!containerRef.current || mapRef.current) return

    let cancelled = false

    import('leaflet').then((L) => {
      if (cancelled || !containerRef.current) return

      const map = L.map(containerRef.current).setView([39.5, -98.0], 4)
      mapRef.current = map

      L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> &copy; <a href="https://carto.com/">CARTO</a>',
        maxZoom: 18,
      }).addTo(map)

      layersRef.current = L.layerGroup().addTo(map)
    })

    return () => {
      cancelled = true
      mapRef.current?.remove()
      mapRef.current = null
      layersRef.current = null
    }
  }, [])

  // Update corridor layers when data changes
  useEffect(() => {
    const map = mapRef.current
    const layers = layersRef.current
    if (!map || !layers) return

    import('leaflet').then((L) => {
      layers.clearLayers()

      for (const c of corridors) {
        if (c.origin_lat == null || c.origin_lon == null || c.dest_lat == null || c.dest_lon == null) continue

        const isSelected = c.corridor_id === selectedCorridorId
        const tons = c.total_tons ?? 0
        const weight = Math.max(2, Math.min(8, tons / 50000))

        // Corridor polyline
        const line = L.polyline(
          [[c.origin_lat, c.origin_lon], [c.dest_lat, c.dest_lon]],
          {
            color: isSelected ? '#ffffff' : '#38bdf8',
            weight: isSelected ? weight + 2 : weight,
            opacity: isSelected ? 1 : 0.6,
            dashArray: isSelected ? undefined : '8 4',
          },
        )
        line.on('click', () => onCorridorSelect(c))
        line.bindTooltip(c.name, { sticky: true, className: 'freight-tooltip' })
        layers.addLayer(line)

        // Origin marker
        const originCircle = L.circleMarker([c.origin_lat, c.origin_lon], {
          radius: isSelected ? 8 : 6,
          fillColor: '#22c55e',
          color: isSelected ? '#ffffff' : '#22c55e',
          weight: isSelected ? 2 : 1,
          fillOpacity: 0.8,
        })
        originCircle.bindTooltip(c.name.split(' → ')[0] ?? 'Origin', { className: 'freight-tooltip' })
        originCircle.on('click', () => onCorridorSelect(c))
        layers.addLayer(originCircle)

        // Destination marker
        const destCircle = L.circleMarker([c.dest_lat, c.dest_lon], {
          radius: isSelected ? 8 : 6,
          fillColor: '#ef4444',
          color: isSelected ? '#ffffff' : '#ef4444',
          weight: isSelected ? 2 : 1,
          fillOpacity: 0.8,
        })
        destCircle.bindTooltip(c.name.split(' → ')[1] ?? 'Destination', { className: 'freight-tooltip' })
        destCircle.on('click', () => onCorridorSelect(c))
        layers.addLayer(destCircle)
      }
    })
  }, [corridors, selectedCorridorId, onCorridorSelect])

  return <div ref={containerRef} style={{ height: '100%', width: '100%' }} />
}
