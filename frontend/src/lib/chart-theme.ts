import type { CSSProperties } from 'react'

/** Shared Recharts tooltip style — matches shadcn dark theme */
export const chartTooltipStyle: CSSProperties = {
  backgroundColor: 'var(--card)',
  border: '1px solid var(--border)',
  borderRadius: '8px',
  fontSize: '12px',
  color: 'var(--foreground)',
}

/** Recharts axis tick style */
export const chartAxisTick = { fontSize: 10, fill: 'var(--muted-foreground)' }

/** Recharts grid stroke color */
export const chartGridStroke = 'var(--border)'

/** Data visualization colors — use these for chart series */
export const chartColors = {
  sky: '#38bdf8',
  green: '#22c55e',
  red: '#ef4444',
  orange: '#f59e0b',
  purple: '#a78bfa',
  cyan: '#06b6d4',
} as const
