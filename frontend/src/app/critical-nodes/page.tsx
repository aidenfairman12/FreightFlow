'use client'

import { useState, useEffect, useCallback } from 'react'
import dynamic from 'next/dynamic'
import Link from 'next/link'
import { AlertTriangle, ArrowRight, Layers } from 'lucide-react'
import { data } from '@/lib/api'
import type { CriticalNode } from '@/types'

const CriticalNodesMap = dynamic(
  () => import('@/components/Map/CriticalNodesMap'),
  { ssr: false, loading: () => <div className="h-full w-full animate-pulse bg-white/5" /> },
)

// ── Colour scale (matches map) ────────────────────────────────────────────
function scoreColor(score: number): string {
  if (score >= 0.15) return '#ef4444'
  if (score >= 0.06) return '#f97316'
  if (score >= 0.03) return '#f59e0b'
  return '#facc15'
}

function scoreTier(score: number): string {
  if (score >= 0.15) return 'Critical'
  if (score >= 0.06) return 'High'
  if (score >= 0.03) return 'Moderate'
  return 'Low'
}

// Unique product names from a node's affected list
function productNames(node: CriticalNode): string[] {
  return [...new Set(node.products_affected.map(p => p.product_name))]
}

// ── Format helpers ────────────────────────────────────────────────────────
function fmt(n: number, d = 1): string {
  if (n >= 1e9) return `${(n / 1e9).toFixed(d)}B`
  if (n >= 1e6) return `${(n / 1e6).toFixed(d)}M`
  if (n >= 1e3) return `${(n / 1e3).toFixed(d)}K`
  return n.toFixed(d)
}
function fmtTons(tons_k: number) { return fmt(tons_k * 1_000) }

// ── Node detail panel ─────────────────────────────────────────────────────
function NodeDetail({ node }: { node: CriticalNode }) {
  const color   = scoreColor(node.systemic_score)
  const tier    = scoreTier(node.systemic_score)
  const pct     = Math.round(node.systemic_score * 100)
  const products = productNames(node)

  return (
    <div className="flex flex-col gap-4">
      {/* Header */}
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="flex items-center gap-2">
            <div className="h-3 w-3 rounded-full" style={{ backgroundColor: color }} />
            <h3 className="text-sm font-bold text-white">{node.zone_name}</h3>
          </div>
          <p className="mt-0.5 text-xs text-white/40">{node.state} · Rank #{node.rank}</p>
        </div>
        <span
          className="shrink-0 rounded-full px-2.5 py-0.5 text-[11px] font-semibold"
          style={{ backgroundColor: `${color}22`, color, border: `1px solid ${color}55` }}
        >
          {tier}
        </span>
      </div>

      {/* Systemic score bar */}
      <div>
        <div className="mb-1 flex items-baseline justify-between text-xs">
          <span className="text-white/40">Systemic impact score</span>
          <span className="font-bold text-white">{pct}%</span>
        </div>
        <div className="h-2 w-full overflow-hidden rounded-full bg-white/10">
          <div
            className="h-full rounded-full"
            style={{ width: `${Math.min(pct * 5, 100)}%`, backgroundColor: color }}
          />
        </div>
        <p className="mt-1 text-[10px] text-white/30">
          % of all modelled US supply chain precursor inputs
        </p>
      </div>

      {/* KPIs */}
      <div className="grid grid-cols-2 gap-2">
        {[
          { label: 'Tonnage gap',   value: `${fmtTons(node.total_tons_k)} t` },
          { label: 'Cost impact',   value: `$${fmt(node.total_cost_usd)}` },
          { label: 'Products hit',  value: String(products.length) },
          { label: 'Supply chains', value: String(node.products_affected.length) },
        ].map(k => (
          <div key={k.label} className="rounded-lg bg-white/4 px-3 py-2">
            <div className="text-[10px] text-white/35">{k.label}</div>
            <div className="text-sm font-bold text-white">{k.value}</div>
          </div>
        ))}
      </div>

      {/* Per-product breakdown */}
      <div>
        <div className="mb-2 text-[10px] font-semibold uppercase tracking-wider text-white/30">
          Impact by supply chain
        </div>
        <div className="flex flex-col gap-2">
          {node.products_affected.map((p, i) => {
            const precPct = Math.round(p.pct_of_precursor * 100)
            const prodPct = Math.round(p.pct_of_product * 100)
            return (
              <div key={i} className="rounded-lg border border-white/6 bg-white/3 px-3 py-2.5">
                <div className="mb-1.5 flex items-center justify-between">
                  <span className="text-xs font-semibold text-white/80">{p.product_name}</span>
                  <span className="font-mono text-[10px] text-white/40">{fmtTons(p.tons_k)} t</span>
                </div>
                <div className="text-[10px] text-white/45 mb-1.5">
                  via {p.precursor_name}
                </div>
                <div className="flex gap-3 text-[11px]">
                  <div>
                    <span className="text-white/30">of precursor </span>
                    <span className="font-semibold" style={{ color: precPct >= 50 ? '#ef4444' : precPct >= 20 ? '#f97316' : '#f59e0b' }}>
                      {precPct}%
                    </span>
                  </div>
                  <div>
                    <span className="text-white/30">of product inputs </span>
                    <span className="font-semibold text-white/70">{prodPct}%</span>
                  </div>
                </div>
                {/* Mini bar for precursor share */}
                <div className="mt-1.5 h-1 w-full overflow-hidden rounded-full bg-white/10">
                  <div
                    className="h-full rounded-full"
                    style={{
                      width: `${precPct}%`,
                      backgroundColor: precPct >= 50 ? '#ef4444' : precPct >= 20 ? '#f97316' : '#f59e0b',
                      opacity: 0.7,
                    }}
                  />
                </div>
              </div>
            )
          })}
        </div>
      </div>

      {/* Link to explorer for dominant product */}
      <Link
        href={`/explorer?product=${node.products_affected[0]?.sctg2}`}
        className="flex items-center justify-between rounded-xl border border-sky-500/20 bg-sky-500/8 px-4 py-3 text-xs text-sky-400 transition-colors hover:border-sky-500/40 hover:bg-sky-500/15"
      >
        <span>Explore {node.products_affected[0]?.product_name} supply chain</span>
        <ArrowRight className="h-3.5 w-3.5" />
      </Link>
    </div>
  )
}

// ── Main page ─────────────────────────────────────────────────────────────
export default function CriticalNodesPage() {
  const [nodes, setNodes]           = useState<CriticalNode[]>([])
  const [loading, setLoading]       = useState(true)
  const [selectedId, setSelectedId] = useState<number | null>(null)

  useEffect(() => { document.title = 'Critical Nodes | FreightFlow' }, [])
  useEffect(() => {
    data.criticalNodes().then(n => { setNodes(n); setLoading(false) })
  }, [])

  const handleNodeClick = useCallback((node: CriticalNode) => {
    setSelectedId(prev => prev === node.zone_id ? null : node.zone_id)
  }, [])

  const selectedNode = nodes.find(n => n.zone_id === selectedId) ?? null
  const criticalCount = nodes.filter(n => n.systemic_score >= 0.06).length

  return (
    <div className="flex h-full flex-col overflow-hidden">
      {/* ── Top bar ──────────────────────────────────────────── */}
      <div className="flex shrink-0 items-center gap-3 border-b border-white/6 px-5 py-3">
        <AlertTriangle className="h-4 w-4 text-orange-400" />
        <span className="text-xs font-semibold text-white/70">Critical Nodes</span>
        <span className="text-white/15">·</span>
        <span className="text-xs text-white/35">Cross-supply-chain systemic risk by source zone</span>
        {!loading && criticalCount > 0 && (
          <span className="ml-auto rounded-full border border-orange-400/30 bg-orange-400/10 px-2.5 py-0.5 text-[11px] font-semibold text-orange-300">
            {criticalCount} high-risk zones
          </span>
        )}
      </div>

      {/* ── Main layout ──────────────────────────────────────── */}
      <div className="flex flex-1 overflow-hidden">
        {/* Map */}
        <div className="relative flex-1">
          {loading ? (
            <div className="absolute inset-0 flex items-center justify-center">
              <div className="h-6 w-6 animate-spin rounded-full border-2 border-sky-400 border-t-transparent" />
            </div>
          ) : (
            <CriticalNodesMap
              nodes={nodes}
              selectedNodeId={selectedId}
              onNodeClick={handleNodeClick}
            />
          )}

          {/* Legend */}
          {!loading && (
            <div className="pointer-events-none absolute bottom-8 left-4 rounded-xl border border-white/10 bg-black/70 px-3 py-2.5 backdrop-blur-sm">
              <div className="mb-1.5 text-[9px] font-semibold uppercase tracking-wider text-white/40">
                Systemic score
              </div>
              {[
                { label: '≥ 15%', color: '#ef4444' },
                { label: '6–15%', color: '#f97316' },
                { label: '3–6%',  color: '#f59e0b' },
                { label: '< 3%',  color: '#facc15' },
              ].map(e => (
                <div key={e.label} className="flex items-center gap-2 text-[10px] text-white/60">
                  <div className="h-2.5 w-2.5 rounded-full" style={{ backgroundColor: e.color }} />
                  {e.label}
                </div>
              ))}
              <div className="mt-1.5 text-[9px] text-white/30">Node size = tonnage impact</div>
            </div>
          )}
        </div>

        {/* Sidebar */}
        <div className="flex w-72 shrink-0 flex-col overflow-hidden border-l border-white/6 bg-background">
          {/* Header */}
          <div className="shrink-0 border-b border-white/6 px-4 py-4">
            <div className="flex items-center gap-2 mb-1">
              <AlertTriangle className="h-4 w-4 text-orange-400" />
              <h2 className="text-sm font-bold text-white">Critical Nodes</h2>
            </div>
            <p className="text-[11px] leading-relaxed text-white/40">
              Source zones ranked by systemic impact across all supply chains.
              {!loading && criticalCount > 0 && (
                <> <span className="text-orange-400 font-medium">{criticalCount} zones</span> pose high or critical risk.</>
              )}
            </p>
          </div>

          {selectedNode ? (
            /* Detail view */
            <div className="flex-1 overflow-y-auto px-4 py-4">
              <button
                onClick={() => setSelectedId(null)}
                className="mb-3 flex items-center gap-1 text-[11px] text-white/30 hover:text-white/60 transition-colors"
              >
                ← All nodes
              </button>
              <NodeDetail node={selectedNode} />
            </div>
          ) : (
            /* Ranked list */
            <div className="flex-1 overflow-y-auto px-3 py-3">
              <div className="flex flex-col gap-1">
                {nodes.map(node => {
                  const color    = scoreColor(node.systemic_score)
                  const products = productNames(node)
                  const pct      = Math.round(node.systemic_score * 100)
                  const isMulti  = products.length > 1

                  return (
                    <button
                      key={node.zone_id}
                      onClick={() => handleNodeClick(node)}
                      className="group flex items-center gap-3 rounded-lg px-2.5 py-2 text-left transition-colors hover:bg-white/5"
                    >
                      {/* Rank */}
                      <span className="w-5 shrink-0 font-mono text-[10px] text-white/25 text-right">
                        {node.rank}
                      </span>

                      {/* Color dot */}
                      <div
                        className="h-2 w-2 shrink-0 rounded-full"
                        style={{ backgroundColor: color }}
                      />

                      {/* Name + products */}
                      <div className="min-w-0 flex-1">
                        <div className="truncate text-xs font-medium text-white/80">
                          {node.zone_name}
                        </div>
                        <div className="flex items-center gap-1 mt-0.5">
                          {isMulti && (
                            <Layers className="h-2.5 w-2.5 text-sky-400 shrink-0" />
                          )}
                          <span className="truncate text-[10px] text-white/35">
                            {products.join(' · ')}
                          </span>
                        </div>
                      </div>

                      {/* Score */}
                      <div className="shrink-0 text-right">
                        <div
                          className="font-mono text-xs font-semibold"
                          style={{ color }}
                        >
                          {pct}%
                        </div>
                      </div>
                    </button>
                  )
                })}
              </div>

              <p className="mt-4 px-2 text-[9px] leading-relaxed text-white/20">
                FAF5 v5.7.1 · 2022 data · BTS/FHWA<br />
                Score = % of all modelled precursor tonnage supplied by this zone.<br />
                <Layers className="inline h-2.5 w-2.5 mr-0.5" />= affects multiple supply chains
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
