'use client'

import { useEffect } from 'react'
import { useLeafletMap } from '@/hooks/useLeafletMap'
import type { PrecursorDetail, SourceZone, AssemblyZoneData } from '@/types'

interface ColoredPrecursor extends PrecursorDetail {
  color: string
}

interface Props {
  assemblyZone: AssemblyZoneData | null
  precursorFlows: ColoredPrecursor[]
  highlightedPrecursor: string | null
  disruptedZoneIds?: number[]
  onSourceClick?: (source: SourceZone) => void
}

// Visual constants
const MAX_LINE_WEIGHT = 12   // px — top source in any precursor group
const MIN_LINE_WEIGHT = 1.5  // px — smallest visible line
const MAX_NODE_RADIUS = 13   // px
const MIN_NODE_RADIUS = 6    // px — large enough to click reliably
const HIT_LINE_WEIGHT = 16   // px — invisible wider line for click detection

export default function SupplyChainMap({
  assemblyZone,
  precursorFlows,
  highlightedPrecursor,
  disruptedZoneIds = [],
  onSourceClick,
}: Props) {
  const { containerRef, mapRef, leafletRef, layersRef, mapReady } = useLeafletMap()

  useEffect(() => {
    const L      = leafletRef.current
    const layers = layersRef.current
    const map    = mapRef.current
    if (!L || !layers || !map) return

    layers.clearLayers()

    if (!assemblyZone?.latitude || !assemblyZone?.longitude) return

    const bounds = L.latLngBounds([[assemblyZone.latitude, assemblyZone.longitude]])
    const azLat  = assemblyZone.latitude
    const azLon  = assemblyZone.longitude

    for (const group of precursorFlows) {
      const isActive      = !highlightedPrecursor || highlightedPrecursor === group.sctg2
      const lineOpacity   = isActive ? 0.72 : 0.06
      const markerOpacity = isActive ? 0.92 : 0.08

      // Normalize weights within this precursor group so the top source
      // always gets the max visual weight regardless of absolute pct values.
      // This makes concentration legible whether it's 1 source at 99%
      // or 20 sources each at 5%.
      const maxPct = group.sources.reduce((m, s) => Math.max(m, s.pct_of_precursor), 0.001)

      for (const src of group.sources) {
        if (!src.latitude || !src.longitude) continue

        bounds.extend([src.latitude, src.longitude])

        const isDisrupted = disruptedZoneIds.includes(src.zone_id)
        const normPct     = src.pct_of_precursor / maxPct   // 0–1 relative to group max

        const lineWeight  = MIN_LINE_WEIGHT + normPct * (MAX_LINE_WEIGHT - MIN_LINE_WEIGHT)
        const nodeRadius  = MIN_NODE_RADIUS + normPct * (MAX_NODE_RADIUS - MIN_NODE_RADIUS)

        const lineColor   = isDisrupted ? '#ef4444' : group.color
        const mOpacity    = isDisrupted ? 1.0 : markerOpacity

        const pctLabel = fmtPct(src.pct_of_precursor)
        const costM    = (src.est_cost_usd / 1_000_000).toFixed(1)
        const tooltip  = `<strong>${src.zone_name}</strong><br/>`
          + `<span style="color:${group.color}">${group.name}</span><br/>`
          + `${pctLabel} of supply · ${src.primary_mode}<br/>`
          + `Est. cost: $${costM}M`
          + (isDisrupted ? '<br/><span style="color:#ef4444">⚠ Disrupted</span>' : '')

        // ── Visual line ─────────────────────────────────────────
        const visLine = L.polyline(
          [[src.latitude, src.longitude], [azLat, azLon]],
          {
            color:     lineColor,
            weight:    isDisrupted ? Math.max(lineWeight, 3) : lineWeight,
            opacity:   isDisrupted ? 0.95 : lineOpacity,
            dashArray: isDisrupted ? '6 4' : undefined,
          },
        )
        visLine.bindTooltip(tooltip, { sticky: true, className: 'freight-tooltip' })
        layers.addLayer(visLine)

        // ── Invisible hit-area line (wider, transparent) ────────
        // Makes thin lines clickable without changing their appearance
        if (onSourceClick) {
          const hitLine = L.polyline(
            [[src.latitude, src.longitude], [azLat, azLon]],
            { color: '#ffffff', weight: HIT_LINE_WEIGHT, opacity: 0, interactive: true },
          )
          hitLine.bindTooltip(tooltip, { sticky: true, className: 'freight-tooltip' })
          hitLine.on('click', (e: L.LeafletMouseEvent) => {
            L.DomEvent.stopPropagation(e)
            onSourceClick(src)
          })
          layers.addLayer(hitLine)
        }

        // ── Source marker ───────────────────────────────────────
        const marker = L.circleMarker([src.latitude, src.longitude], {
          radius:      isDisrupted ? Math.max(nodeRadius, 8) : nodeRadius,
          fillColor:   lineColor,
          color:       isDisrupted ? '#ffffff' : 'rgba(0,0,0,0.3)',
          weight:      isDisrupted ? 2 : 1,
          fillOpacity: mOpacity,
        })
        marker.bindTooltip(
          `${src.zone_name} · ${pctLabel}` + (isDisrupted ? ' ⚠' : ''),
          { className: 'freight-tooltip' },
        )
        if (onSourceClick) {
          marker.on('click', (e: L.LeafletMouseEvent) => {
            L.DomEvent.stopPropagation(e)
            onSourceClick(src)
          })
        }
        layers.addLayer(marker)
      }
    }

    // Assembly zone — large white dot, always on top
    const assemblyMarker = L.circleMarker([azLat, azLon], {
      radius:      13,
      fillColor:   '#ffffff',
      color:       '#38bdf8',
      weight:      3,
      fillOpacity: 0.95,
    })
    assemblyMarker.bindTooltip(
      `<strong>${assemblyZone.zone_name}</strong><br/>Assembly / Production Zone`,
      { className: 'freight-tooltip' },
    )
    layers.addLayer(assemblyMarker)

    if (bounds.isValid()) {
      map.fitBounds(bounds, { padding: [50, 50], maxZoom: 7 })
    }
  }, [assemblyZone, precursorFlows, highlightedPrecursor, disruptedZoneIds, onSourceClick, mapReady])

  return <div ref={containerRef} style={{ height: '100%', width: '100%' }} />
}

// ── Helpers (local, not exported) ─────────────────────────────────────────
function fmtPct(ratio: number): string {
  const pct = Math.round(ratio * 100)
  if (pct === 0 && ratio > 0) return '< 1%'
  return `${pct}%`
}
