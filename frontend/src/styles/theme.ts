import type { CSSProperties } from 'react'

export const colors = {
  bg: '#0f172a',
  card: '#1e293b',
  cardHover: '#263548',
  border: '#334155',
  text: '#f1f5f9',
  textMuted: '#94a3b8',
  textDim: '#64748b',
  accent: '#38bdf8',
  green: '#22c55e',
  red: '#ef4444',
  orange: '#f59e0b',
  purple: '#a78bfa',
  cyan: '#06b6d4',
} as const

export const cardStyle: CSSProperties = {
  background: colors.card,
  borderRadius: 8,
  padding: 16,
}

export const labelStyle: CSSProperties = {
  fontSize: 11,
  color: colors.textMuted,
  textTransform: 'uppercase',
  letterSpacing: '0.05em',
  marginBottom: 8,
}

export const tooltipStyle: CSSProperties = {
  background: colors.bg,
  border: `1px solid ${colors.border}`,
  fontSize: 12,
}

export const buttonStyle: CSSProperties = {
  padding: '6px 14px',
  borderRadius: 6,
  border: `1px solid ${colors.border}`,
  background: colors.card,
  color: colors.text,
  fontSize: 13,
  cursor: 'pointer',
}

export const buttonPrimaryStyle: CSSProperties = {
  ...buttonStyle,
  background: colors.accent,
  borderColor: colors.accent,
  color: colors.bg,
  fontWeight: 600,
}
