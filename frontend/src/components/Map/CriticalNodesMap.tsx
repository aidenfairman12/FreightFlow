'use client'

import { useEffect } from 'react'
import { useLeafletMap } from '@/hooks/useLeafletMap'
import type { CriticalNode } from '@/types'

// Color scale: low systemic score → yellow, high → red
function scoreColor(score: number): string {
  if (score >= 0.15) return '#ef4444'   // red   — 15%+
  if (score >= 0.06) return '#f97316'   // orange — 6–15%
  if (score >= 0.03) return '#f59e0b'   // amber  — 3–6%
  return '#facc15'                       // yellow — < 3%
}

interface Props {
  nodes: CriticalNode[]
  selectedNodeId: number | null
  onNodeClick: (node: CriticalNode) => void
}

export default function CriticalNodesMap({ nodes, selectedNodeId, onNodeClick }: Props) {
  const { containerRef, mapRef, leafletRef, layersRef, mapReady } = useLeafletMap()

  useEffect(() => {
    const L      = leafletRef.current
    const layers = layersRef.current
    const map    = mapRef.current
    if (!L || !layers || !map || nodes.length === 0) return

    layers.clearLayers()

    const maxTons = nodes[0]?.total_tons_k ?? 1   // nodes sorted desc by tonnage

    for (const node of nodes) {
      const isSelected = node.zone_id === selectedNodeId
      const color      = scoreColor(node.systemic_score)
      const normSize   = node.total_tons_k / maxTons           // 0–1
      const radius     = Math.max(6, normSize * 28)             // 6–28 px
      const products   = [...new Set(node.products_affected.map(p => p.product_name))]
      const pctLabel   = `${Math.round(node.systemic_score * 100)}%`

      // Invisible hit-area ring for easy clicking
      const hitMarker = L.circleMarker([node.lat, node.lon], {
        radius:      radius + 8,
        fillColor:   'transparent',
        color:       'transparent',
        weight:      0,
        fillOpacity: 0,
        interactive: true,
      })
      hitMarker.on('click', () => onNodeClick(node))
      layers.addLayer(hitMarker)

      // Visual marker
      const marker = L.circleMarker([node.lat, node.lon], {
        radius,
        fillColor:   color,
        color:       isSelected ? '#ffffff' : 'rgba(0,0,0,0.4)',
        weight:      isSelected ? 3 : 1.5,
        fillOpacity: isSelected ? 1.0 : 0.75,
      })

      marker.bindTooltip(
        `<strong>#${node.rank} ${node.zone_name}</strong><br/>`
        + `Systemic score: <strong>${pctLabel}</strong> of all inputs<br/>`
        + `Products: ${products.join(', ')}<br/>`
        + `${(node.total_tons_k / 1000).toFixed(1)}M tons · $${(node.total_cost_usd / 1e9).toFixed(2)}B`,
        { sticky: true, className: 'freight-tooltip' },
      )
      marker.on('click', () => onNodeClick(node))
      layers.addLayer(marker)

      // Rank label for top 5
      if (node.rank <= 5) {
        const icon = L.divIcon({
          className: '',
          html: `<div style="
            color:#fff;font-size:10px;font-weight:700;
            text-shadow:0 1px 3px rgba(0,0,0,0.9);
            pointer-events:none;white-space:nowrap;
          ">#${node.rank}</div>`,
          iconAnchor: [-radius - 2, 6],
        })
        layers.addLayer(L.marker([node.lat, node.lon], { icon, interactive: false }))
      }
    }

    // Fit to CONUS
    map.setView([39.5, -97], 4)
  }, [nodes, selectedNodeId, onNodeClick, mapReady])

  return <div ref={containerRef} style={{ height: '100%', width: '100%' }} />
}
