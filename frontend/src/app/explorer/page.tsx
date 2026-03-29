'use client'

import { useState, useMemo, useCallback, useEffect, Suspense } from 'react'
import { useSearchParams } from 'next/navigation'
import dynamic from 'next/dynamic'
import { AlertTriangle, ChevronLeft, X, Zap } from 'lucide-react'
import { data } from '@/lib/api'
import type {
  Product,
  SupplyChainData,
  AssemblyZoneData,
  PrecursorDetail,
  SourceZone,
  DisruptionResult,
} from '@/types'

const SupplyChainMap = dynamic(
  () => import('@/components/Map/SupplyChainMap'),
  { ssr: false, loading: () => <div className="h-full w-full animate-pulse bg-white/5" /> },
)

// ── Colour palette ────────────────────────────────────────────────────────
const PRECURSOR_COLORS = [
  '#38bdf8', '#f59e0b', '#a78bfa', '#22c55e',
  '#ef4444', '#06b6d4', '#fb923c', '#e879f9',
] as const

function assignColors(precursors: PrecursorDetail[]) {
  return precursors.map((p, i) => ({
    ...p,
    color: PRECURSOR_COLORS[i % PRECURSOR_COLORS.length],
  }))
}

// ── Formatting ────────────────────────────────────────────────────────────
function fmt(n: number, decimals = 1): string {
  if (n >= 1_000_000_000) return `${(n / 1_000_000_000).toFixed(decimals)}B`
  if (n >= 1_000_000)     return `${(n / 1_000_000).toFixed(decimals)}M`
  if (n >= 1_000)         return `${(n / 1_000).toFixed(decimals)}K`
  return n.toFixed(decimals)
}

// tons_k is stored in thousands → display as actual tons
function fmtTons(tons_k: number): string {
  return fmt(tons_k * 1_000)
}

function fmtPct(ratio: number): string {
  const pct = Math.round(ratio * 100)
  if (pct === 0 && ratio > 0) return '< 1%'
  return `${pct}%`
}

// ── Multi-zone disruption simulation ─────────────────────────────────────
function computeDisruption(
  zone: AssemblyZoneData,
  zoneIds: number[],
): DisruptionResult | null {
  if (zoneIds.length === 0) return null

  let totalGap  = 0
  let totalCost = 0
  const perPrecursor = []

  for (const prec of zone.precursors) {
    let precGap  = 0
    let precCost = 0
    for (const zid of zoneIds) {
      const src = prec.sources.find(s => s.zone_id === zid)
      if (!src) continue
      precGap  += src.tons_k
      precCost += src.est_cost_usd
    }
    if (precGap > 0) {
      totalGap  += precGap
      totalCost += precCost
      perPrecursor.push({
        name:             prec.name,
        sctg2:            prec.sctg2,
        tons_k:           precGap,
        pct_of_precursor: prec.total_tons_k > 0 ? precGap / prec.total_tons_k : 0,
      })
    }
  }

  if (totalGap === 0) return null

  const totalPrecursorTons = zone.precursors.reduce((s, p) => s + p.total_tons_k, 0)

  // Collect zone names for all selected IDs
  const allSources = zone.precursors.flatMap(p => p.sources)
  const names = zoneIds.map(
    id => allSources.find(s => s.zone_id === id)?.zone_name ?? `Zone ${id}`,
  )

  return {
    disrupted_zone_ids:   zoneIds,
    disrupted_zone_names: [...new Set(names)],
    tonnage_gap_k:        totalGap,
    cost_impact_usd:      totalCost,
    pct_of_total:         totalPrecursorTons > 0 ? totalGap / totalPrecursorTons : 0,
    per_precursor:        perPrecursor,
  }
}

// ── Disruption panel ──────────────────────────────────────────────────────
function DisruptionPanel({
  result,
  onClear,
}: {
  result: DisruptionResult
  onClear: () => void
}) {
  const pct      = Math.round(result.pct_of_total * 100)
  const severity = pct >= 40 ? 'critical' : pct >= 20 ? 'high' : 'moderate'
  const colors   = {
    critical: 'border-red-500/40 bg-red-500/10',
    high:     'border-orange-400/40 bg-orange-400/10',
    moderate: 'border-yellow-400/40 bg-yellow-400/10',
  }

  const zoneLabel = result.disrupted_zone_names.length === 1
    ? result.disrupted_zone_names[0]
    : `${result.disrupted_zone_names.length} zones`

  return (
    <div className={`rounded-xl border p-4 ${colors[severity]}`}>
      {/* Header */}
      <div className="mb-3 flex items-start justify-between gap-2">
        <div className="flex items-center gap-2">
          <AlertTriangle className="h-4 w-4 shrink-0 text-white/70" />
          <span className="text-sm font-semibold text-white">
            Disruption: {zoneLabel}
          </span>
        </div>
        <button onClick={onClear} className="rounded p-0.5 text-white/40 hover:text-white/80">
          <X className="h-3.5 w-3.5" />
        </button>
      </div>

      {/* Top KPIs */}
      <div className="mb-3 grid grid-cols-2 gap-3 text-xs">
        <div>
          <div className="text-white/40">Tonnage gap</div>
          <div className="text-lg font-bold text-white">{fmtTons(result.tonnage_gap_k)} tons</div>
        </div>
        <div>
          <div className="text-white/40">% of all inputs</div>
          <div className="text-lg font-bold text-white">{fmtPct(result.pct_of_total)}</div>
        </div>
        <div>
          <div className="text-white/40">Annual cost impact</div>
          <div className="font-semibold text-white">${fmt(result.cost_impact_usd)}</div>
        </div>
        <div>
          <div className="text-white/40">Zones disrupted</div>
          <div className="font-semibold text-white">{result.disrupted_zone_ids.length}</div>
        </div>
      </div>

      {/* Per-precursor breakdown — explains the math */}
      <div className="space-y-1.5 border-t border-white/10 pt-3">
        <div className="mb-1.5 text-[9px] font-semibold uppercase tracking-wider text-white/30">
          Impact by material
        </div>
        {result.per_precursor.map(p => (
          <div key={p.sctg2} className="flex items-center justify-between text-[11px]">
            <span className="text-white/60">{p.name}</span>
            <div className="flex items-center gap-2">
              <span className="font-mono text-white/40">{fmtTons(p.tons_k)} t</span>
              <span className={`min-w-[36px] text-right font-semibold ${
                p.pct_of_precursor >= 0.5 ? 'text-red-400' :
                p.pct_of_precursor >= 0.2 ? 'text-orange-400' : 'text-yellow-400'
              }`}>
                {fmtPct(p.pct_of_precursor)}
              </span>
            </div>
          </div>
        ))}
      </div>

      {/* Multi-zone list */}
      {result.disrupted_zone_names.length > 1 && (
        <div className="mt-3 border-t border-white/10 pt-2">
          <div className="text-[9px] font-semibold uppercase tracking-wider text-white/30 mb-1">
            Disrupted zones
          </div>
          <div className="text-[11px] text-white/50">
            {result.disrupted_zone_names.join(' · ')}
          </div>
        </div>
      )}
    </div>
  )
}

// ── Main page ─────────────────────────────────────────────────────────────
function ExplorerContent() {
  const searchParams   = useSearchParams()
  const initialProduct = searchParams.get('product') ?? ''

  const [products, setProducts]       = useState<Product[]>([])
  const [selectedProduct, setProduct] = useState(initialProduct)
  const [supplyChain, setSupplyChain] = useState<SupplyChainData | null>(null)
  const [loading, setLoading]         = useState(false)
  const [highlighted, setHighlighted] = useState<string | null>(null)

  // Multi-zone disruption state
  const [disruptedIds, setDisruptedIds] = useState<number[]>([])

  // Page title
  useEffect(() => { document.title = 'Explorer | FreightFlow' }, [])

  // Load product list once
  useEffect(() => {
    data.products().then(setProducts)
  }, [])

  // Load supply chain when product changes
  useEffect(() => {
    if (!selectedProduct) return
    setLoading(true)
    setSupplyChain(null)
    setDisruptedIds([])
    setHighlighted(null)
    data.supplyChain(selectedProduct)
      .then(sc => setSupplyChain(sc))
      .finally(() => setLoading(false))
  }, [selectedProduct])

  // Always use first assembly zone (headline, sorted first by precompute script)
  const activeZone = useMemo<AssemblyZoneData | null>(
    () => supplyChain?.assembly_zones[0] ?? null,
    [supplyChain],
  )

  const coloredPrecursors = useMemo(
    () => (activeZone ? assignColors(activeZone.precursors) : []),
    [activeZone],
  )

  // Toggle a source zone in/out of the disrupted set
  const handleSourceClick = useCallback(
    (src: SourceZone) => {
      if (!activeZone) return
      setDisruptedIds(prev =>
        prev.includes(src.zone_id)
          ? prev.filter(id => id !== src.zone_id)
          : [...prev, src.zone_id],
      )
    },
    [activeZone],
  )

  const clearDisruption = useCallback(() => setDisruptedIds([]), [])

  // Recompute disruption result whenever selected zones change
  const disruption = useMemo<DisruptionResult | null>(
    () => (activeZone && disruptedIds.length > 0
      ? computeDisruption(activeZone, disruptedIds)
      : null),
    [activeZone, disruptedIds],
  )

  // Totals
  const totalTons  = activeZone?.total_precursor_tons_k ?? 0
  const totalCost  = activeZone?.total_est_cost_usd ?? 0
  const numSources = useMemo(
    () => new Set(coloredPrecursors.flatMap(p => p.sources.map(s => s.zone_id))).size,
    [coloredPrecursors],
  )

  return (
    <div className="flex h-full flex-col overflow-hidden">
      {/* ── Top bar ─────────────────────────────────────────── */}
      <div className="flex shrink-0 items-center border-b border-white/6 px-5 py-3">
        {/* Left — breadcrumb */}
        <div className="flex flex-1 items-center gap-1">
          <a href="/" className="flex items-center gap-1 text-xs text-white/30 hover:text-white/60 transition-colors">
            <ChevronLeft className="h-3 w-3" /> Overview
          </a>
          <span className="text-white/15">/</span>
          <span className="text-xs font-medium text-white/60">Supply Chain Explorer</span>
        </div>

        {/* Centre — product selector */}
        <div className="flex items-center gap-2">
          <span className="text-xs font-medium text-white/50">Product</span>
          <select
            value={selectedProduct}
            onChange={e => { setProduct(e.target.value); setHighlighted(null) }}
            className="rounded-lg border border-sky-500/50 bg-sky-500/10 px-3 py-1.5 text-sm font-medium text-white focus:outline-none focus:ring-1 focus:ring-sky-400"
          >
            <option value="" disabled>Select product…</option>
            {products.map(p => (
              <option key={p.sctg2} value={p.sctg2}>{p.name}</option>
            ))}
          </select>
        </div>

        {/* Right — spacer to balance breadcrumb */}
        <div className="flex-1" />
      </div>

      {/* ── Main layout ──────────────────────────────────────── */}
      <div className="flex flex-1 overflow-hidden">
        {/* Map */}
        <div className="relative flex-1">
          {loading && (
            <div className="absolute inset-0 z-10 flex items-center justify-center bg-background/80 backdrop-blur-sm">
              <div className="h-6 w-6 animate-spin rounded-full border-2 border-sky-400 border-t-transparent" />
            </div>
          )}
          {!selectedProduct && (
            <div className="absolute inset-0 z-10 flex items-center justify-center bg-background/50">
              <p className="text-sm text-white/40">Select a product above to visualise its supply chain</p>
            </div>
          )}

          <SupplyChainMap
            assemblyZone={activeZone}
            precursorFlows={coloredPrecursors}
            highlightedPrecursor={highlighted}
            disruptedZoneIds={disruptedIds}
            onSourceClick={handleSourceClick}
          />

          {/* Hint overlay */}
          {activeZone && disruptedIds.length === 0 && (
            <div className="pointer-events-none absolute bottom-4 left-1/2 -translate-x-1/2 rounded-full border border-white/10 bg-black/60 px-3 py-1.5 backdrop-blur-sm">
              <p className="flex items-center gap-1.5 text-[11px] text-white/50">
                <Zap className="h-3 w-3 text-yellow-400" />
                Click source zones to simulate disruptions — stack multiple zones
              </p>
            </div>
          )}
        </div>

        {/* Sidebar */}
        {activeZone && (
          <div className="flex w-72 shrink-0 flex-col gap-4 overflow-y-auto border-l border-white/6 bg-background px-4 py-4">
            {/* Title */}
            <div>
              <h2 className="text-sm font-bold text-white">{supplyChain?.name}</h2>
              <p className="text-xs text-white/40">{activeZone.zone_name} · {activeZone.state}</p>
            </div>

            {/* Disruption panel */}
            {disruption && (
              <DisruptionPanel result={disruption} onClear={clearDisruption} />
            )}

            {/* KPIs */}
            <div className="grid grid-cols-2 gap-2">
              {[
                { label: 'Precursor tons', value: fmtTons(totalTons) },
                { label: 'Est. cost',      value: `$${fmt(totalCost)}` },
                { label: 'Source zones',   value: String(numSources) },
                { label: 'Data year',      value: '2022' },
              ].map(k => (
                <div key={k.label} className="rounded-lg bg-white/4 px-3 py-2">
                  <div className="text-[10px] text-white/35">{k.label}</div>
                  <div className="text-sm font-bold text-white">{k.value}</div>
                </div>
              ))}
            </div>

            {/* Precursor breakdown */}
            <div>
              <div className="mb-2 text-[10px] font-semibold uppercase tracking-wider text-white/30">
                Precursor inputs
              </div>
              <div className="flex flex-col gap-2">
                {coloredPrecursors.map(p => (
                  <button
                    key={p.sctg2}
                    onClick={() => setHighlighted(highlighted === p.sctg2 ? null : p.sctg2)}
                    className={`rounded-lg border px-3 py-2.5 text-left transition-all duration-150 ${
                      highlighted === p.sctg2
                        ? 'border-white/20 bg-white/8'
                        : 'border-white/5 bg-white/3 hover:border-white/10'
                    }`}
                  >
                    <div className="flex items-center gap-2">
                      <div className="h-2 w-2 rounded-full shrink-0" style={{ backgroundColor: p.color }} />
                      <span className="text-xs font-medium text-white/80">{p.name}</span>
                      <span className="ml-auto font-mono text-[10px] text-white/40">{fmtTons(p.total_tons_k)}</span>
                    </div>
                    <div className="mt-1 pl-4 text-[10px] text-white/35">{p.role}</div>
                    {p.sources.length > 0 && (() => {
                      const top = p.sources[0]
                      return (
                        <div className="mt-2 pl-4">
                          <div className="mb-0.5 flex justify-between text-[9px] text-white/25">
                            <span>Top source: {top.zone_name}</span>
                            <span>{fmtPct(top.pct_of_precursor)}</span>
                          </div>
                          <div className="h-1 rounded-full bg-white/10">
                            <div
                              className="h-full rounded-full transition-all"
                              style={{
                                width: `${Math.round(top.pct_of_precursor * 100)}%`,
                                backgroundColor: p.color,
                                opacity: 0.7,
                              }}
                            />
                          </div>
                        </div>
                      )
                    })()}
                  </button>
                ))}
              </div>
            </div>

            {/* Source zone table for highlighted precursor */}
            {highlighted && (() => {
              const prec = coloredPrecursors.find(p => p.sctg2 === highlighted)
              if (!prec) return null
              return (
                <div>
                  <div className="mb-2 text-[10px] font-semibold uppercase tracking-wider text-white/30">
                    {prec.name} — source zones
                  </div>
                  <div className="flex flex-col gap-0.5">
                    {prec.sources.map(src => {
                      const isDisrupted = disruptedIds.includes(src.zone_id)
                      return (
                        <div
                          key={src.zone_id}
                          onClick={() => handleSourceClick(src)}
                          className={`flex cursor-pointer items-center justify-between rounded-lg px-2.5 py-1.5 text-[11px] transition-colors ${
                            isDisrupted
                              ? 'bg-red-500/20 text-red-300'
                              : 'text-white/60 hover:bg-white/5'
                          }`}
                          title="Click to toggle disruption"
                        >
                          <div className="flex items-center gap-1.5 truncate">
                            {isDisrupted && <span className="shrink-0 text-[9px]">⚠</span>}
                            <span className="truncate">{src.zone_name}</span>
                          </div>
                          <span className="ml-2 shrink-0 font-mono text-white/40">
                            {fmtPct(src.pct_of_precursor)}
                          </span>
                        </div>
                      )
                    })}
                  </div>
                </div>
              )
            })()}

            {/* Data note */}
            <p className="mt-auto text-[9px] leading-relaxed text-white/20">
              FAF5 v5.7.1 · 2022 data · BTS/FHWA<br />
              Click zones on the map or list to add/remove from disruption scenario
            </p>
          </div>
        )}
      </div>

    </div>
  )
}

export default function ExplorerPage() {
  return (
    <Suspense fallback={<div className="h-full animate-pulse bg-white/5" />}>
      <ExplorerContent />
    </Suspense>
  )
}
