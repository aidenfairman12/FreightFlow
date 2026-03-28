'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { AlertTriangle, ChevronRight, Truck } from 'lucide-react'
import { data } from '@/lib/api'
import type { RiskScore } from '@/types'

const TIER_CONFIG = {
  critical: {
    label: 'Critical',
    bar: 'bg-red-500',
    badge: 'bg-red-500/15 text-red-400 border border-red-500/30',
    glow: 'shadow-red-500/10',
  },
  high: {
    label: 'High',
    bar: 'bg-orange-400',
    badge: 'bg-orange-400/15 text-orange-300 border border-orange-400/30',
    glow: 'shadow-orange-400/10',
  },
  medium: {
    label: 'Medium',
    bar: 'bg-yellow-400',
    badge: 'bg-yellow-400/15 text-yellow-300 border border-yellow-400/30',
    glow: 'shadow-yellow-400/10',
  },
  low: {
    label: 'Low',
    bar: 'bg-emerald-500',
    badge: 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/30',
    glow: 'shadow-emerald-500/10',
  },
} as const

function ConcentrationBar({ value, tier }: { value: number; tier: RiskScore['risk_tier'] }) {
  const cfg = TIER_CONFIG[tier]
  return (
    <div className="relative h-1.5 w-full overflow-hidden rounded-full bg-white/10">
      <div
        className={`h-full rounded-full transition-all duration-700 ${cfg.bar}`}
        style={{ width: `${Math.round(value * 100)}%` }}
      />
    </div>
  )
}

/**
 * Shorten a FAF5 zone name for compact display in a card.
 * Strips trailing state codes like " TX", " NY-NJ-CT-PA (NJ Part)", etc.
 * Examples:
 *   "Baton Rouge LA"                       → "Baton Rouge"
 *   "West Virginia"                         → "West Virginia"  (no code to strip)
 *   "Minneapolis-St. Paul MN-WI (MN Part)" → "Minneapolis-St. Paul"
 *   "New York NY-NJ-CT-PA (NY Part)"       → "New York"
 *   "Chicago Metro"                         → "Chicago Metro"
 */
function shortZoneName(name: string): string {
  const stripped = name
    .replace(/\s+[A-Z]{2}(-[A-Z]{2})*(\s*\([^)]*\))?$/, '')
    .trim()
  return stripped || name
}

function RiskCard({ score, rank }: { score: RiskScore; rank: number }) {
  const cfg = TIER_CONFIG[score.risk_tier]
  const pct = Math.round(score.concentration_top3 * 100)
  const top3names = score.top_source_zones.slice(0, 3).map(z => shortZoneName(z.zone_name)).join(', ')

  return (
    <Link
      href={`/explorer?product=${score.sctg2}`}
      className={`group relative flex flex-col gap-4 rounded-2xl border border-white/8 bg-white/4 p-6 backdrop-blur-sm transition-all duration-200 hover:border-white/16 hover:bg-white/7 hover:shadow-xl ${cfg.glow}`}
    >
      {/* Rank + tier badge */}
      <div className="flex items-center justify-between">
        <span className="font-mono text-xs text-white/30">#{rank}</span>
        <span className={`rounded-full px-2.5 py-0.5 text-[11px] font-semibold uppercase tracking-wide ${cfg.badge}`}>
          {cfg.label} Risk
        </span>
      </div>

      {/* Product name + description */}
      <div>
        <h3 className="text-lg font-bold text-white">{score.name}</h3>
        <p className="mt-1 text-xs leading-relaxed text-white/50 line-clamp-2">
          {score.top_source_zones[0]?.zone_name && (
            <>Primary {score.primary_precursor.toLowerCase()} supply: {top3names} and {score.num_source_zones - 3} other zones</>
          )}
        </p>
      </div>

      {/* Concentration metric */}
      <div className="space-y-2">
        <div className="flex items-baseline justify-between">
          <span className="text-xs text-white/40">
            Top-3 source concentration
          </span>
          <span className="text-2xl font-extrabold tabular-nums text-white">
            {pct}<span className="text-base font-semibold text-white/60">%</span>
          </span>
        </div>
        <ConcentrationBar value={score.concentration_top3} tier={score.risk_tier} />
      </div>

      {/* Key insight line */}
      <p className="text-[11px] leading-relaxed text-white/35">
        Measured at <span className="text-white/55">{score.top_assembly_zone}</span> · {score.primary_precursor}
      </p>

      {/* Hover arrow */}
      <ChevronRight className="absolute right-5 top-1/2 h-4 w-4 -translate-y-1/2 text-white/20 transition-all duration-200 group-hover:translate-x-0.5 group-hover:text-white/50" />
    </Link>
  )
}

export default function RiskOverviewPage() {
  const [scores, setScores] = useState<RiskScore[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => { document.title = 'FreightFlow — Risk Overview' }, [])
  useEffect(() => {
    data.riskScores().then(s => { setScores(s); setLoading(false) })
  }, [])

  const criticalCount = scores.filter(s => s.risk_tier === 'critical').length
  const highestPct    = scores[0] ? Math.round(scores[0].concentration_top3 * 100) : 0

  return (
    <div className="flex h-full flex-col overflow-y-auto bg-background">
      {/* ── Header ──────────────────────────────────────────── */}
      <div className="border-b border-white/6 px-8 py-10">
        <div className="mx-auto max-w-4xl">
          <div className="mb-2 flex items-center gap-2.5">
            <Truck className="h-5 w-5 text-sky-400" />
            <span className="text-xs font-semibold uppercase tracking-widest text-sky-400/80">FreightFlow</span>
          </div>
          <h1 className="text-3xl font-extrabold tracking-tight text-white">
            US Supply Chain Risk Overview
          </h1>
          <p className="mt-2 max-w-xl text-sm leading-relaxed text-white/50">
            Concentration risk analysis for four critical US supply chains — ranked by fragility.
            Based on FAF5 freight flow data (2022) from the Bureau of Transportation Statistics.
          </p>

          {/* Summary callout */}
          {!loading && scores.length > 0 && (
            <div className="mt-6 inline-flex items-start gap-3 rounded-xl border border-red-500/25 bg-red-500/8 px-4 py-3">
              <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-red-400" />
              <p className="text-xs leading-relaxed text-white/70">
                <span className="font-semibold text-white">{criticalCount} of {scores.length} supply chains</span> show{' '}
                critical concentration risk. The most extreme: {scores[0]?.name} inputs are{' '}
                <span className="font-semibold text-red-300">{highestPct}% concentrated</span> in just three source zones.
              </p>
            </div>
          )}
        </div>
      </div>

      {/* ── Cards grid ──────────────────────────────────────── */}
      <div className="flex-1 px-8 py-8">
        <div className="mx-auto max-w-4xl">
          {loading ? (
            <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
              {[1, 2, 3, 4].map(i => (
                <div key={i} className="h-52 animate-pulse rounded-2xl bg-white/5" />
              ))}
            </div>
          ) : (
            <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
              {scores.map((score, i) => (
                <RiskCard key={score.sctg2} score={score} rank={i + 1} />
              ))}
            </div>
          )}

          {/* Methodology note */}
          <p className="mt-8 text-center text-[11px] text-white/25">
            Concentration = % of primary precursor tonnage entering the headline assembly zone
            from top-3 external source zones &middot; FAF5 v5.7.1, 2022 &middot; BTS/FHWA
          </p>
        </div>
      </div>
    </div>
  )
}
