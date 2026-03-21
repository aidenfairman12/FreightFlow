import type { CSSProperties, ReactNode } from 'react'
import { colors, cardStyle, labelStyle } from '@/styles/theme'

interface CardProps {
  title?: string
  children: ReactNode
  style?: CSSProperties
}

export function Card({ title, children, style }: CardProps) {
  return (
    <div style={{ ...cardStyle, ...style }}>
      {title && <div style={labelStyle}>{title}</div>}
      {children}
    </div>
  )
}
